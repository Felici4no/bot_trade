import time
import threading
import tkinter as tk
from tkinter import scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from binance.client import Client
import os

# ============ CONFIGURAÇÃO ============ #
API_KEY = os.getenv("API_KEY") or "U2xBIMnmAB89r0g8yu0yxE8pFKavFPw03KaV2vy0ai5L41kB3npc0ukDdoTWlD1U"
API_SECRET = os.getenv("API_SECRET") or "zO0lxc78mfY1Ycc9Vlq1viBTB5rmYHoxgTvZaULSq81jNClFi196B7rGPZMHa9cz"
SYMBOL = "BTCUSDT"

N = 20
FATOR = 2.5
INVEST_POR_ORDEM = 100
TAXA = 0.00075
INTERVALO = 5  # Reduzido para testes

client = Client(API_KEY, API_SECRET)
precos = []
rsi_valores = []
saldo_simulado = 1000.0
historico_operacoes = []
posicoes_abertas = []  # Agora pode conter várias posições


# ============ INTERFACE GRÁFICA ============ #
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bot BTC - Monitor em Tempo Real")
        self.geometry("1200x800")

        self.fig, (self.ax, self.ax_rsi) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [2, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=140, height=15)
        self.log_area.pack(pady=10)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self, textvariable=self.status_var, font=("Arial", 12, "bold"))
        self.status_label.pack()

        self.protocol("WM_DELETE_WINDOW", self.salvar_antes_de_sair)
        self.iniciar_thread()

    def log(self, mensagem):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {mensagem}\n")
        self.log_area.see(tk.END)
        self.update_status()

    def update_status(self):
        status_text = f"💰 Saldo: ${saldo_simulado:.2f} | Operações: {len(historico_operacoes)}"
        if posicoes_abertas:
            status_text += f" | Posições Abertas: {len(posicoes_abertas)}"
        self.status_var.set(status_text)

    def atualizar_grafico(self):
        try:
            self.ax.clear()
            self.ax.plot(precos[-100:], label='Preço', color='blue')

            if len(precos) >= N:
                bandas = self.calcular_bandas()
                self.ax.plot([bandas['media']] * len(precos[-100:]), linestyle='--', color='grey', label='MM20')
                self.ax.plot([bandas['superior']] * len(precos[-100:]), linestyle='--', color='red', label='Banda Superior')
                self.ax.plot([bandas['inferior']] * len(precos[-100:]), linestyle='--', color='green', label='Banda Inferior')

            self.ax.set_title("Preço do BTC em Tempo Real")
            self.ax.legend(loc='upper left')

            self.ax_rsi.clear()
            self.ax_rsi.plot(rsi_valores[-100:], color='orange', label='RSI')
            self.ax_rsi.axhline(30, color='green', linestyle='--')
            self.ax_rsi.axhline(70, color='red', linestyle='--')
            self.ax_rsi.set_title("RSI 14 Períodos")

            self.canvas.draw()

        except Exception as e:
            self.log(f"Erro no gráfico: {str(e)}")

    def calcular_bandas(self):
        media = np.mean(precos[-N:])
        std = np.std(precos[-N:])
        return {
            'media': media,
            'superior': media + FATOR * std,
            'inferior': media - FATOR * std
        }

    def salvar_transacoes_excel(self):
        try:
            df = pd.DataFrame(historico_operacoes)
            df.to_excel("transacoes_btc.xlsx", index=False)
            self.log("📁 Transações salvas em 'transacoes_btc.xlsx'")
        except Exception as e:
            self.log(f"Erro ao salvar Excel: {str(e)}")

    def salvar_antes_de_sair(self):
        self.salvar_transacoes_excel()
        self.destroy()

    def iniciar_thread(self):
        def estrategia():
            global saldo_simulado
            while True:
                try:
                    novo_preco = float(client.get_symbol_ticker(symbol=SYMBOL)['price'])
                    precos.append(novo_preco)

                    if len(precos) >= 15:
                        rsi_valores.append(RSIIndicator(pd.Series(precos), window=14).rsi().iloc[-1])

                    self.after(0, self.atualizar_grafico)
                    self.after(0, self.log, f"Preço atualizado: ${novo_preco:.2f}")

                    if len(precos) >= N:
                        bandas = self.calcular_bandas()
                        if novo_preco <= bandas['inferior'] and rsi_valores[-1] < 35:
                            if saldo_simulado >= INVEST_POR_ORDEM:
                                nova_posicao = {
                                    'preco': novo_preco,
                                    'qtd': (INVEST_POR_ORDEM / novo_preco) * (1 - TAXA),
                                    'hora': time.time()
                                }
                                posicoes_abertas.append(nova_posicao)
                                saldo_simulado -= INVEST_POR_ORDEM
                                self.after(0, self.log, f"COMPRA: {nova_posicao['qtd']:.6f} BTC @ ${novo_preco:.2f}")

                        for posicao in posicoes_abertas[:]:
                            lucro_atual = (novo_preco - posicao['preco']) / posicao['preco']
                            if lucro_atual >= 0.005 or lucro_atual <= -0.003:
                                valor_venda = posicao['qtd'] * novo_preco * (1 - TAXA)
                                saldo_simulado += valor_venda
                                operacao = {
                                    'hora': time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'compra': posicao['preco'],
                                    'venda': novo_preco,
                                    'lucro': valor_venda - INVEST_POR_ORDEM
                                }
                                historico_operacoes.append(operacao)

                                self.after(0, self.log,
                                           f"VENDA: Lucro ${valor_venda - INVEST_POR_ORDEM:.2f} ({lucro_atual:.2%})")
                                self.after(0, self.salvar_transacoes_excel)
                                posicoes_abertas.remove(posicao)

                    time.sleep(INTERVALO)

                except Exception as e:
                    self.after(0, self.log, f"ERRO: {str(e)}")
                    time.sleep(5)

        thread = threading.Thread(target=estrategia, daemon=True)
        thread.start()


if __name__ == "__main__":
    app = Application()
    app.mainloop()
