import pandas as pd
import numpy as np

def run_performance_audit(price_df, engine_df):
    """
    Calculates Alpha, Max Drawdown, and Sharpe improvement.
    Compares Buy & Hold (S&P 500) vs VETOS Fail-Closed Strategy.
    """
    # 1. Align Data
    audit = price_df[['sp500']].join(engine_df)
    audit['returns'] = audit['sp500'].pct_change()
    
    # 2. Apply VETOS Strategy (Lagged by 1 period to prevent look-ahead bias)
    # Strategy: 100% SPY if CLEAR, 0% (Cash/Halt) if QUARANTINE
    audit['position'] = (~audit['quarantine_signal']).shift(1).fillna(1)
    audit['strat_returns'] = audit['returns'] * audit['position']
    
    # 3. Cumulative Wealth
    audit['bh_wealth'] = (1 + audit['returns']).cumprod()
    audit['strat_wealth'] = (1 + audit['strat_returns']).cumprod()
    
    # 4. Drawdown Calculation
    def get_max_dd(series):
        peak = series.cummax()
        dd = (series - peak) / peak
        return dd.min()

    metrics = {
        "CAGR_BH": (audit['bh_wealth'].iloc[-1]**(1/(len(audit)/12))) - 1,
        "CAGR_VETOS": (audit['strat_wealth'].iloc[-1]**(1/(len(audit)/12))) - 1,
        "MaxDD_BH": get_max_dd(audit['bh_wealth']),
        "MaxDD_VETOS": get_max_dd(audit['strat_wealth']),
        "Sharpe_BH": (audit['returns'].mean() / audit['returns'].std()) * np.sqrt(12),
        "Sharpe_VETOS": (audit['strat_returns'].mean() / audit['strat_returns'].std()) * np.sqrt(12)
    }
    
    print("\n--- PERFORMANCE AUDIT RESULTS ---")
    print(f"B&H Max Drawdown:    {metrics['MaxDD_BH']:.2%}")
    print(f"VETOS Max Drawdown:  {metrics['MaxDD_VETOS']:.2%}")
    print(f"Sharpe Improvement:  {metrics['Sharpe_VETOS'] - metrics['Sharpe_BH']:.2f}")
    
    return metrics
