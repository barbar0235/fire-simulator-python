import tkinter as tk
from tkinter import messagebox
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

plt.rcParams['font.family'] = 'MS Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 【データ一括取得】
print("初期データを準備中...（数秒かかります）")
sp500_long = yf.download("^GSPC", start="2004-01-01", auto_adjust=True)['Close']
usdjpy_long = yf.download("JPY=X", start="2004-01-01", auto_adjust=True)['Close']
df_long = pd.concat([sp500_long, usdjpy_long], axis=1).dropna()
df_long.columns = ['sp_price', 'fx_rate']
df_long['SP500_LONG'] = df_long['sp_price'] * df_long['fx_rate']

df_etf = yf.download(["2559.T", "2558.T"], start="2020-01-01", auto_adjust=True)['Close']
df_etf = df_etf.dropna()
df_etf.columns = ['SP500_ETF', 'OLKAN']

def on_fund_change():
    selected_fund = var_fund.get()
    current_year = entry_year.get()
    
    if selected_fund == "SP500_LONG":
        if not current_year.isdigit() or int(current_year) < 2004 or int(current_year) == 2020:
            entry_year.delete(0, tk.END)
            entry_year.insert(0, "2004")
    else:
        if not current_year.isdigit() or int(current_year) < 2020:
            entry_year.delete(0, tk.END)
            entry_year.insert(0, "2020")
            
    run_simulation()

def run_simulation(target_year=None):
    try:
        if target_year:
            start_year = str(target_year)
            entry_year.delete(0, tk.END)
            entry_year.insert(0, start_year)
        else:
            start_year = entry_year.get()
        
        initial_taxable = float(entry_taxable.get()) * 10000
        initial_nisa = float(entry_nisa.get()) * 10000
        monthly_withdrawal = float(entry_withdrawal.get()) * 10000
        
        selected_fund = var_fund.get()
        start_date = f"{start_year}-01-01"
        tax_rate = 0.20315
        
        label_status.config(text="計算中...", fg="blue")
        root.update()
        
        if selected_fund == "SP500_LONG":
            df_target = df_long['SP500_LONG']
            min_year, max_year = 2004, 2026
        elif selected_fund == "SP500_ETF":
            df_target = df_etf['SP500_ETF']
            min_year, max_year = 2020, 2026
        else:
            df_target = df_etf['OLKAN']
            min_year, max_year = 2020, 2026

        if not (min_year <= int(start_year) <= max_year):
            raise IndexError
            
        df = df_target.loc[start_date:]
        if df.empty:
            raise ValueError

        taxable = initial_taxable
        nisa = initial_nisa
        history = []
        returns = df.pct_change().fillna(0)

        current_month = -1
        for date, r in returns.items():
            taxable *= (1 + r)
            nisa *= (1 + r)
            
            if date.month != current_month:
                if taxable > monthly_withdrawal:
                    taxable -= monthly_withdrawal / (1 - tax_rate)
                else:
                    nisa -= monthly_withdrawal
                current_month = date.month
            
            # 資産がマイナスにならないようにストッパー
            taxable = max(0.0, taxable)
            nisa = max(0.0, nisa)
            
            total_assets = taxable + nisa
            history.append({
                'Date': date, 
                'Taxable': taxable, 
                'NISA': nisa, 
                'Total': total_assets
            })

        res = pd.DataFrame(history).set_index('Date')
        
        # --- 【新機能】最終結果を左下のラベルに表示する処理 ---
        final_taxable_man = res['Taxable'].iloc[-1] / 10000
        final_nisa_man = res['NISA'].iloc[-1] / 10000
        final_total_man = res['Total'].iloc[-1] / 10000
        
        label_final_taxable.config(text=f"特定口座: {final_taxable_man:,.0f} 万円")
        label_final_nisa.config(text=f"NISA口座: {final_nisa_man:,.0f} 万円")
        label_final_total.config(text=f"合計資産: {final_total_man:,.0f} 万円")
        
        # --- グラフの描画 ---
        ax1.clear()
        ax2.clear()
        
        names = {"SP500_LONG": "S&P500(長期2004~)", "SP500_ETF": "eMAXIS Slim S&P500仕様(2020~)", "OLKAN": "eMAXIS Slim オルカン仕様(2020~)"}
        fund_name = names[selected_fund]
        
        ax1.plot(res['Total'] / 1000000, label='合計資産 (Total)', color='purple', linewidth=2)
        ax1.plot(res['Taxable'] / 1000000, label='特定口座 (Taxable)', color='C0', alpha=0.6)
        ax1.plot(res['NISA'] / 1000000, label='NISA口座', color='C1', alpha=0.6)
        ax1.set_title(f"FIRE Simulation [{fund_name}] (Start: {start_year})", fontsize=11, fontweight='bold')
        ax1.set_ylabel("資産 (百万円)")
        ax1.grid(True)
        ax1.legend()
        
        ax2.plot(df_target, label=f'{fund_name} 全期間チャート', color='green')
        ax2.axvline(pd.to_datetime(start_date), color='red', linestyle='--', linewidth=2, label='Current Start')
        ax2.set_title("★下のグラフをクリックすると、その年からシミュレーションを開始します★", fontsize=10, color='darkgreen')
        ax2.set_ylabel("基準値ベース")
        ax2.grid(True)
        ax2.legend()
        
        fig.tight_layout()
        canvas.draw()
        
        label_status.config(text=f"計算完了！({start_year}年開始)", fg="green")
        
    except (ValueError, KeyError, IndexError):
        label_status.config(text="エラー", fg="red")
        if selected_fund == "SP500_LONG":
            messagebox.showerror("エラー", "S&P500(長期)は、2004〜2026年の間で入力してください。")
        else:
            messagebox.showerror("エラー", "投信仕様(2020〜)データのため、2020〜2026年の間で入力してください。")

def on_click(event):
    if event.inaxes == ax2:
        click_date = mdates.num2date(event.xdata)
        click_year = click_date.year
        selected_fund = var_fund.get()
        min_y = 2004 if selected_fund == "SP500_LONG" else 2020
        if min_y <= click_year <= 2026:
            run_simulation(target_year=click_year)

# --- 画面（ウインドウ）の作成 ---
root = tk.Tk()
root.title("超多機能・投資信託＆米国株FIREシミュレーター")
root.geometry("1150x820") # 少し縦幅を広げました

frame_left = tk.Frame(root, width=280, padx=20, pady=20)
frame_left.pack(side=tk.LEFT, fill=tk.Y)

frame_right = tk.Frame(root, bg="white")
frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# 投資先の選択
tk.Label(frame_left, text="投資先・データ期間の選択:", font=("MS Gothic", 10, "bold")).pack(anchor="w", pady=5)
var_fund = tk.StringVar(value="SP500_LONG")

rb_sp_long = tk.Radiobutton(frame_left, text="S&P500 (長期:2004〜)", variable=var_fund, value="SP500_LONG", command=on_fund_change)
rb_sp_long.pack(anchor="w")
rb_olkan = tk.Radiobutton(frame_left, text="全世界株式 オルカン (2020〜)", variable=var_fund, value="OLKAN", command=on_fund_change)
rb_olkan.pack(anchor="w")
rb_sp_etf = tk.Radiobutton(frame_left, text="S&P500 投信仕様 (2020〜)", variable=var_fund, value="SP500_ETF", command=on_fund_change)
rb_sp_etf.pack(anchor="w", pady=(0, 15))

# 入力欄
tk.Label(frame_left, text="開始年 (西暦):").pack(anchor="w", pady=2)
entry_year = tk.Entry(frame_left, font=("Arial", 11))
entry_year.insert(0, "2004")
entry_year.pack(fill="x", pady=5)

tk.Label(frame_left, text="特定口座の資産 (万円):").pack(anchor="w", pady=2)
entry_taxable = tk.Entry(frame_left, font=("Arial", 11))
entry_taxable.insert(0, "2000")
entry_taxable.pack(fill="x", pady=5)

tk.Label(frame_left, text="NISA口座の資産 (万円):").pack(anchor="w", pady=2)
entry_nisa = tk.Entry(frame_left, font=("Arial", 11))
entry_nisa.insert(0, "1800")
entry_nisa.pack(fill="x", pady=5)

tk.Label(frame_left, text="毎月の取り崩し額 (万円):").pack(anchor="w", pady=2)
entry_withdrawal = tk.Entry(frame_left, font=("Arial", 11))
entry_withdrawal.insert(0, "20")
entry_withdrawal.pack(fill="x", pady=5)

tk.Button(frame_left, text="手動で計算実行", command=lambda: run_simulation(), bg="orange", fg="black", font=("MS Gothic", 12, "bold"), height=2).pack(fill="x", pady=20)
label_status = tk.Label(frame_left, text="グラフをクリックしてみよう！", font=("MS Gothic", 10, "bold"), fg="darkgreen")
label_status.pack(fill="x", pady=(0, 20))

# --- 【新機能】左下のシミュレーション最終結果の表示枠 ---
frame_result = tk.LabelFrame(frame_left, text=" シミュレーション最終結果 ", font=("MS Gothic", 10, "bold"), padx=10, pady=10)
frame_result.pack(fill="x", side=tk.BOTTOM)

label_final_taxable = tk.Label(frame_result, text="特定口座: - 万円", font=("Arial", 11), anchor="w")
label_final_taxable.pack(fill="x", pady=2)

label_final_nisa = tk.Label(frame_result, text="NISA口座: - 万円", font=("Arial", 11), anchor="w")
label_final_nisa.pack(fill="x", pady=2)

# 合計だけ少し太字で目立たせる
label_final_total = tk.Label(frame_result, text="合計資産: - 万円", font=("Arial", 11, "bold"), fg="purple", anchor="w")
label_final_total.pack(fill="x", pady=5)

# 上下に2つのグラフ
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 6))
canvas = FigureCanvasTkAgg(fig, master=frame_right)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

fig.canvas.mpl_connect('button_press_event', on_click)

run_simulation()

root.mainloop()