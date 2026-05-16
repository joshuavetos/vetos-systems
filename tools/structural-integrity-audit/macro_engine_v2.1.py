import os

import numpy as np
import yfinance as yf
from arch import arch_model
from fredapi import Fred


class VetosProportionalController:
    def __init__(self):
        # Fail-Closed Config: Enforce API keys exist even if not currently used
        self.api_key = os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError("Configuration Error: FRED_API_KEY not found in environment.")
        self.fred = Fred(api_key=self.api_key)

    def run_engine(self, start_date: str, end_date: str):
        """
        Executes the VETOS Risk Logic:
        1. GARCH(1,1) Volatility Extraction
        2. Bond Trap Detection (Correlation Interlock)
        3. NEA-Audit (Entropy Deception Detection)
        4. Fail-Closed Exposure Sizing
        """
        tickers = ["SPY", "TLT", "DX-Y.NYB"]
        try:
            raw_data = yf.download(
                tickers, start=start_date, end=end_date, auto_adjust=True, progress=False
            )
        except Exception as e:
            raise RuntimeError(f"Data Feed Failure: {e}") from e

        # 1. Preprocessing
        if "Close" not in raw_data.columns:
            raise ValueError("Malformed Data: 'Close' column missing.")

        df = raw_data["Close"].rename(columns={"DX-Y.NYB": "DXY"}).dropna()
        rets = df.pct_change().dropna()

        # 2. GARCH(1,1) Volatility Extraction
        # We model the 'Natural' volatility of the S&P 500
        garch_input = rets["SPY"] * 100
        am = arch_model(garch_input, vol="Garch", p=1, q=1, dist="Normal")
        res = am.fit(disp="off")

        df["current_vol"] = (res.conditional_volatility / 100) * np.sqrt(252)

        # 3. Structural Baselines
        # Target Vol = Long-term Noise Floor (proxy for natural entropy)
        # We use a 5-year rolling median to establish the 'Physics' of the market
        df["target_vol"] = (
            df["current_vol"].rolling(window=1260, min_periods=252).median().fillna(0.1282)
        )

        # Base Proportional Weight (Uncensored)
        df["prop_weight"] = (df["target_vol"] / df["current_vol"]).clip(0, 1.0)

        # 4. Bond Trap Logic (Liquidity Interlock)
        # Detects when stocks and the dollar correlate during volatility expansion.
        # This marks systemic liquidity failure.
        df["corr_spy_dxy"] = rets["SPY"].rolling(63).corr(rets["DXY"])
        df["trap_signal"] = (df["corr_spy_dxy"].abs() > 0.80) & (
            df["current_vol"] > df["target_vol"]
        )

        # 5. NEA-Audit Protocol (Deception Detector)
        # Strategic Actors suppress volatility to hide drift.
        # If observed noise is < 40% of the natural floor, the stability is FAKE.
        vol_floor = 1e-6
        target_vol_denominator = df["target_vol"].clip(lower=vol_floor)
        df["entropy_ratio"] = df["current_vol"] / target_vol_denominator
        df["entropy_veto"] = df["entropy_ratio"] < 0.40

        # 6. Regime Identification & Fail-Closed Enforcement
        conditions = [df["trap_signal"], df["entropy_veto"]]
        choices = ["EXPLOSIVE", "DECEPTIVE"]
        df["regime_status"] = np.select(conditions, choices, default="STABLE")

        # FINAL GATE: If Trap OR Deception is detected, force 0% exposure.
        df["final_weight"] = np.where(
            df["trap_signal"] | df["entropy_veto"], 0.0, df["prop_weight"]
        )

        # Return strict telemetry columns for the Audit Ledger
        return df[["final_weight", "current_vol", "target_vol", "entropy_ratio", "regime_status"]]
