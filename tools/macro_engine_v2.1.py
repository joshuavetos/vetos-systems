import yfinance as yf
import pandas as pd
import numpy as np
from arch import arch_model
from fredapi import Fred

class VetosProportionalController:
    """
    VETOS v6.0: Proportional Risk Controller
    Implements Recursive GARCH Mean-Reversion and Cross-Asset 'Bond Trap' Detection.
    """
    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def run_engine(self, start_date: str, end_date: str):
        # 1. Fetch Multi-Asset Stack
        tickers = ["SPY", "TLT", "DX-Y.NYB"]
        raw_data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True)
        df = raw_data['Close'].rename(columns={"DX-Y.NYB": "DXY"}).dropna()
        rets = df.pct_change().dropna()

        # 2. Recursive GARCH Mean-Reversion (Vol Targeting)
        garch_input = rets['SPY'] * 100
        am = arch_model(garch_input, vol='Garch', p=1, q=1, dist='Normal')
        res = am.fit(disp='off')
        
        df['current_vol'] = (res.conditional_volatility / 100) * np.sqrt(252)
        df['target_vol'] = df['current_vol'].rolling(window=252*5, min_periods=252).median().fillna(0.15)

        # 3. Proportional Scaling (The 'Dimmer Switch')
        df['prop_weight'] = (df['target_vol'] / df['current_vol']).clip(0, 1.0)

        # 4. Bond Trap Detection (Systemic Liquidity Kill-Switch)
        df['corr_spy_dxy'] = rets['SPY'].rolling(63).corr(rets['DXY'])
        # Trap: Deep Dollar/Equity coupling + Elevated Volatility
        df['trap_signal'] = (df['corr_spy_dxy'].abs() > 0.80) & (df['current_vol'] > df['target_vol'])

        # 5. Final Decision Gate
        df['final_weight'] = np.where(df['trap_signal'], 0.0, df['prop_weight'])
        
        return df[['final_weight', 'current_vol', 'target_vol', 'trap_signal']]

if __name__ == "__main__":
    # Internal Audit Execution
    controller = VetosProportionalController(api_key="8ceb380a1f418fffa80ce574495f43e9")
    results = controller.run_engine("2005-01-01", "2026-02-11")
    print(f"Current System State: {results['final_weight'].iloc[-1] * 100:.1f}% Exposure")
