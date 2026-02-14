import numpy as np
import scipy.ndimage as ndimage

class LighthouseAgent:
    def __init__(self, agent_id, world_size=100, view_dist=30):
        self.agent_id = agent_id
        self.world_size = world_size
        self.view_dist = view_dist

    def get_lighthouse_signal(self, global_terrain, current_pos):
        """
        Multi-Scale Saliency with Deterministic Tie-Breaking.
        Works on natural terrains by finding the inherent structural 'Center of Mass'.
        """
        r, c = current_pos
        # The 'Squint' area
        macro_dist = self.view_dist * 2 
        r0, r1 = max(0, r-macro_dist), min(self.world_size, r+macro_dist)
        c0, c1 = max(0, c-macro_dist), min(self.world_size, c+macro_dist)
        
        view = global_terrain[r0:r1, c0:c1]
        
        # 1. Macro-Filtering: Find the 'Energy Centers'
        # Sigma is scaled to view_dist to maintain scale-invariance
        blur_sigma = max(1, self.view_dist // 6)
        macro_features = ndimage.gaussian_filter(view, sigma=blur_sigma)
        
        # 2. Tie-Breaking Protocol: 
        # Identify all points within 1% of the local maximum
        max_val = np.max(macro_features)
        candidates = np.argwhere(macro_features >= max_val * 0.99)
        
        # 3. Lexical Sort (Deterministic Anchor):
        # Sort by row, then column. All agents will pick the same 'Top-Left' point.
        # This solves the 'Multiple Peak' problem without communication.
        sorted_candidates = candidates[np.lexsort((candidates[:, 1], candidates[:, 0]))]
        local_idx = sorted_candidates[0]
        
        return (local_idx[0] + r0, local_idx[1] + c0)

    def hunt(self, global_terrain, start_pos, iterations=25):
        curr = np.array(start_pos)
        for _ in range(iterations):
            target = np.array(self.get_lighthouse_signal(global_terrain, tuple(curr)))
            direction = target - curr
            dist = np.linalg.norm(direction)
            
            if dist < 0.5: break # High-precision arrival
            
            # Step size scaled to world size for faster traversal
            step_size = max(2, self.world_size // 15)
            step = (direction / dist) * step_size
            curr = (curr + step).astype(int)
            curr = np.clip(curr, 0, self.world_size - 1)
        return tuple(curr)

def run_natural_test():
    """Stress Test: Coordination on 100% Natural Noise"""
    np.random.seed(99) # Fixed seed for the WORLD, but agents are isolated
    # Natural, rolling terrain with NO artificial lighthouse
    world = ndimage.gaussian_filter(np.random.normal(0, 1, (100, 100)), sigma=3)
    
    agents = [LighthouseAgent(i) for i in range(3)]
    spawns = [(5, 5), (90, 90), (10, 85)]
    final_landings = []

    print("--- NATURAL LIGHTHOUSE: NO ARTIFICIAL PEAKS ---")
    for i, agent in enumerate(agents):
        end_pos = agent.hunt(world, spawns[i])
        final_landings.append(end_pos)
        print(f"Agent {i} | Spawn: {spawns[i]} | Final: {end_pos}")

    # Precision Threshold: Coordination is success if they meet on the same pixel
    success = all(p == final_landings[0] for p in final_landings)
    print("-" * 30)
    print(f"NATURAL COORDINATION: {'SUCCESS' if success else 'FAILURE'}")

if __name__ == "__main__":
    run_natural_test()
