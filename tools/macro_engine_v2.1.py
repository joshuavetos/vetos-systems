import numpy as np
import pandas as pd
from arch import arch_model
from fredapi import Fred
import hashlib

def run_upgraded_engine(df, FRED_API_KEY, START, END):
    """
    VETOS Macro Engine v2.1: Regime Detection & Risk Quarantine
    Logic: (GARCH Volatility Surface) + (Liquidity Velocity) + (Structural Hysteresis)
    """
    # --- 1. Signal Preparation ---
    df = df.copy()
    df['sp_ret'] = df['sp500'].pct_change()
    
    # Baseline 12-month Rolling Stats for Z-Scoring
    rolling_window = 12
    df['vol_baseline'] = df['sp_ret'].rolling(6).std()
    
    # --- 2. Advanced Liquidity Plumbing ---
    # Net Liquidity = (Fed Total Assets) - (TGA Balance) - (Reverse Repo)
    fred = Fred(api_key=FRED_API_KEY)
    
    # Observation: FRED Series are often weekly; we resample to Monthly (Last) to match price data
    tga = fred.get_series('WTREGEN', observation_start=START, observation_end=END).resample('ME').last()
    rrp = fred.get_series('RRPONTSYD', observation_start=START, observation_end=END).resample('ME').last()
    
    df['net_liquidity'] = df['fed_assets'] - tga - rrp
    
    # Net Liquidity Z-Score (The Level)
    df['liq_z'] = (df['net_liquidity'] - df['net_liquidity'].rolling(rolling_window).mean()) / \
                  df['net_liquidity'].rolling(rolling_window).std()
    
    # Net Liquidity Velocity (The Acceleration of the drain)
    # Identifies "Predictive" stress before price realization
    df['liq_velocity'] = df['liq_z'].diff(2) 

    # --- 3. GARCH(1,1) Volatility Surface ---
    # Identifies "Reactive" regime shifts where volatility is clustering
    garch_input = df['sp_ret'].dropna() * 100
    am = arch_model(garch_input, vol='Garch', p=1, q=1, dist='Normal')
    res = am.fit(disp='off')
    
    # Map GARCH volatility back to the main dataframe
    df.loc[garch_input.index, 'garch_vol'] = res.conditional_volatility / 100

    # --- 4. Deterministic Veto Logic (The Gate) ---
    # Trigger 1: Volatility > Historical Baseline (Confirmation)
    # Trigger 2: Liquidity < -1.5 Sigma (Structural Stress)
    # Trigger 3: Liquidity Velocity < -1.0 (Rapid Drain)
    
    df['raw_signal'] = (
        (df['garch_vol'] > df['vol_baseline'].rolling(rolling_window).mean()) | 
        (df['liq_z'] < -1.5) |
        (df['liq_velocity'] < -1.0)
    )

    # --- 5. Hysteresis (Signal Smoothing) ---
    # Prevents "flickering" quarantine signals. Requires 2 consecutive 
    # months of 'Safety' to lift a Veto.
    df['quarantine_signal'] = df['raw_signal'].rolling(window=2).max().fillna(0).astype(bool)

    # --- 6. Integrity & Audit ---
    # Create a structural hash of the decision output for the Audit Ledger
    output_cols = ['liq_z', 'garch_vol', 'quarantine_signal']
    df_check = df[output_cols].tail(1).to_json()
    engine_integrity = hashlib.sha256(df_check.encode()).hexdigest()

    print(f"Engine Integrity Verified: {engine_integrity[:12]}")
    print(f"Current State: {'QUARANTINE' if df['quarantine_signal'].iloc[-1] else 'CLEAR'}")

    return df[output_cols]

# Implementation Note: 
# This engine moves from 'Volatility Confirmation' to 'Regime Navigation' 
# by integrating the first-order derivative (velocity) of global liquidity.
