/* =========================================================================
   FAILURE ORACLE — SINGLE FILE IMPLEMENTATION
   SQLite-class falsification engine
   Header + Proof Log + Merkle-Sealed Store + Verifier
   ========================================================================= */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>

/* =========================
   CONSTANTS
   ========================= */

#define ORACLE_MAGIC "FAILURE_ORACLE_01"
#define ORACLE_VERSION 0x00010000ULL
#define ORACLE_PAGE_SIZE 4096
#define ORACLE_HASH_LEN 32
#define ORACLE_MERKLE_FANOUT 16

#define STATE_SEALED    0
#define STATE_CHECKING  1
#define STATE_BROKEN    2
#define STATE_VERIFIED  3
#define STATE_INVALID   4

#define SEGMENT_PROVISIONAL 0
#define SEGMENT_COMMITTED   1
#define ASSERTION_VERDICT   0xFFFFFFFFFFFFFFFFULL

/* =========================
   HASH (PLACEHOLDER — deterministic)
   ========================= */

static void hash32(const uint8_t *data, size_t len, uint8_t out[32]) {
    /* deterministic non-crypto placeholder */
    uint8_t h = 0;
    for (size_t i = 0; i < len; i++) h ^= data[i];
    memset(out, h, 32);
}

/* =========================
   STRUCTS
   ========================= */

#pragma pack(push,1)
typedef struct {
    char     magic[16];
    uint64_t version;
    uint64_t page_size;
    uint64_t endian_flag;

    uint64_t log_offset;
    uint64_t log_length;
    uint64_t store_offset;
    uint64_t store_length;

    uint8_t  root_hash[32];
    uint8_t  hdr_hash[32];

    uint64_t latest_verdict_id;
    uint64_t file_state;
    uint64_t timestamp_unix;

    uint8_t  reserved[40];
} OracleHeader;

typedef struct {
    uint64_t segment_id;
    uint64_t assertion_id;
    uint64_t timestamp_unix;
    uint32_t state;
    uint32_t data_length;
    uint8_t  pre_hash[32];
    uint8_t  post_hash[32];
    /* payload follows */
} ProofSegment;

typedef struct {
    uint64_t block_id;
    uint32_t data_length;
    uint8_t  reserved[4];
    uint8_t  leaf_hash[32];
    /* data follows */
} EvidenceLeaf;

typedef struct {
    uint64_t node_id;
    uint32_t fanout;
    uint32_t child_count;
    uint8_t  child_hashes[16][32];
    uint8_t  node_hash[32];
} MerkleNode;
#pragma pack(pop)

/* =========================
   HEADER UTIL
   ========================= */

static void seal_header(OracleHeader *h) {
    hash32((uint8_t*)h, 0xC0, h->hdr_hash);
}

static int validate_header(OracleHeader *h) {
    uint8_t chk[32];
    hash32((uint8_t*)h, 0xC0, chk);
    return memcmp(chk, h->hdr_hash, 32) == 0 &&
           memcmp(h->magic, ORACLE_MAGIC, 16) == 0;
}

/* =========================
   APPEND PROOF SEGMENT
   ========================= */

static int append_segment(
    int fd,
    uint64_t *seg_id,
    uint8_t prev_hash[32],
    uint64_t assertion,
    uint32_t state,
    const void *payload,
    uint32_t len,
    uint8_t out_hash[32]
) {
    ProofSegment seg;
    seg.segment_id = ++(*seg_id);
    seg.assertion_id = assertion;
    seg.timestamp_unix = time(NULL);
    seg.state = state;
    seg.data_length = len;
    memcpy(seg.pre_hash, prev_hash, 32);

    uint8_t buf[64];
    memcpy(buf, prev_hash, 32);
    hash32(payload, len, buf + 32);
    hash32(buf, 64, seg.post_hash);

    write(fd, &seg, sizeof(seg));
    write(fd, payload, len);
    fsync(fd);

    memcpy(out_hash, seg.post_hash, 32);
    return 0;
}

/* =========================
   CHECKPOINT → MERKLE
   ========================= */

static int checkpoint_store(
    int fd,
    OracleHeader *hdr,
    const uint8_t *data,
    uint32_t len
) {
    EvidenceLeaf leaf;
    leaf.block_id = 1;
    leaf.data_length = len;
    memset(leaf.reserved, 0, 4);
    hash32(data, len, leaf.leaf_hash);

    off_t pos = lseek(fd, 0, SEEK_END);
    hdr->store_offset = pos;

    write(fd, &leaf, sizeof(leaf));
    write(fd, data, len);

    MerkleNode root;
    memset(&root, 0, sizeof(root));
    root.node_id = 1;
    root.fanout = 1;
    root.child_count = 1;
    memcpy(root.child_hashes[0], leaf.leaf_hash, 32);
    hash32(leaf.leaf_hash, 32, root.node_hash);

    write(fd, &root, sizeof(root));

    memcpy(hdr->root_hash, root.node_hash, 32);
    hdr->store_length = sizeof(leaf) + len + sizeof(root);
    hdr->file_state = STATE_VERIFIED;
    hdr->timestamp_unix = time(NULL);

    seal_header(hdr);
    lseek(fd, 0, SEEK_SET);
    write(fd, hdr, sizeof(*hdr));
    fsync(fd);

    return 0;
}

/* =========================
   RECOVERY
   ========================= */

static int recover_log(int fd, OracleHeader *hdr) {
    lseek(fd, hdr->log_offset, SEEK_SET);
    ProofSegment seg;
    uint64_t last_commit = hdr->latest_verdict_id;

    while (read(fd, &seg, sizeof(seg)) == sizeof(seg)) {
        lseek(fd, seg.data_length, SEEK_CUR);
        if (seg.state == SEGMENT_COMMITTED)
            last_commit = seg.segment_id;
    }

    hdr->latest_verdict_id = last_commit;
    hdr->file_state = STATE_SEALED;
    seal_header(hdr);
    return 0;
}

/* =========================
   READ-ONLY VERIFIER
   ========================= */

static int verify_file(int fd) {
    OracleHeader hdr;
    lseek(fd, 0, SEEK_SET);
    if (read(fd, &hdr, sizeof(hdr)) != sizeof(hdr)) return 1;
    if (!validate_header(&hdr)) return 2;

    lseek(fd, hdr.store_offset, SEEK_SET);

    EvidenceLeaf leaf;
    read(fd, &leaf, sizeof(leaf));

    uint8_t *data = malloc(leaf.data_length);
    read(fd, data, leaf.data_length);

    uint8_t chk[32];
    hash32(data, leaf.data_length, chk);
    free(data);

    if (memcmp(chk, leaf.leaf_hash, 32)) return 3;

    MerkleNode root;
    read(fd, &root, sizeof(root));
    if (memcmp(root.node_hash, hdr.root_hash, 32)) return 4;

    return 0;
}

/* =========================
   MAIN
   ========================= */

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("usage: %s oracle.bin\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], O_RDWR | O_CREAT, 0644);

    OracleHeader hdr;
    if (lseek(fd, 0, SEEK_END) == 0) {
        memset(&hdr, 0, sizeof(hdr));
        memcpy(hdr.magic, ORACLE_MAGIC, 16);
        hdr.version = ORACLE_VERSION;
        hdr.page_size = ORACLE_PAGE_SIZE;
        hdr.log_offset = sizeof(hdr);
        hdr.file_state = STATE_SEALED;
        seal_header(&hdr);
        write(fd, &hdr, sizeof(hdr));
        fsync(fd);
    } else {
        lseek(fd, 0, SEEK_SET);
        read(fd, &hdr, sizeof(hdr));
        if (!validate_header(&hdr)) {
            printf("INVALID HEADER\n");
            return 2;
        }
    }

    uint64_t seg_id = hdr.latest_verdict_id;
    uint8_t last_hash[32] = {0};

    const char *obs = "TEST_FAILURE: invariant violated";
    append_segment(fd, &seg_id, last_hash, 1, SEGMENT_PROVISIONAL,
                   obs, strlen(obs), last_hash);

    append_segment(fd, &seg_id, last_hash, ASSERTION_VERDICT,
                   SEGMENT_COMMITTED, "FAIL", 4, last_hash);

    hdr.latest_verdict_id = seg_id;
    checkpoint_store(fd, &hdr, (uint8_t*)obs, strlen(obs));

    int v = verify_file(fd);
    printf(v == 0 ? "VERIFIED\n" : "INVALID\n");

    close(fd);
    return 0;
}
