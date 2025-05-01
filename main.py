import time
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from binance.client import Client
import os
from datetime import datetime
import requests



# ============ CONFIGURAÇÃO ============ #
API_KEY = os.getenv("API_KEY") or "U2xBIMnmAB89r0g8yu0yxE8pFKavFPw03KaV2vy0ai5L41kB3npc0ukDdoTWlD1U"
API_SECRET = os.getenv("API_SECRET") or "zO0lxc78mfY1Ycc9Vlq1viBTB5rmYHoxgTvZaULSq81jNClFi196B7rGPZMHa9cz"
SYMBOL = "BTCUSDT"

N = 20
FATOR = 2.5
TAXA = 0.00075
INTERVALO = 5  # Reduzido para testes

# ============ GERENCIAMENTO DE RISCOS ============ #
PERDA_POR_OPERACAO_PERCENTUAL = 0.5
RISCO_POR_OPERACAO_PERCENTUAL = 1.0
PERDA_DIARIA_MAXIMA_PERCENTUAL = 2.0

client = Client(API_KEY, API_SECRET)
precos = []
rsi_valores = []
saldo_simulado = 1000.0
historico_operacoes = []
posicoes_abertas = []
perda_diaria_acumulada = 0.0
dia_atual = datetime.now().day
operacoes_hoje = 0
MAX_OPERACOES_POR_DIA = 100
bot_pausado = False

# ============ TELEGRAM CONFIGURAÇÃO ============ #
BOT_TOKEN = "7899777703:AAHXpSnR_1lEaSRGzsxqrHn9-bInXMgpe98"
CHAT_ID = "6083274663"

# Criar arquivos CSV iniciais se não existirem
if not os.path.exists('precos_log.csv'):
    pd.DataFrame(columns=['timestamp', 'preco']).to_csv('precos_log.csv', index=False)
if not os.path.exists('operacoes_log.csv'):
    pd.DataFrame(columns=['hora', 'tipo', 'preco_compra', 'preco_venda', 'quantidade', 'saldo']).to_csv(
        'operacoes_log.csv', index=False)


def calcular_tamanho_posicao(saldo, risco_percentual, preco_ativo):
    """Calcula o tamanho da posição com base no risco percentual do saldo."""
    valor_em_risco = saldo * (risco_percentual / 100)
    quantidade = valor_em_risco / preco_ativo
    return quantidade


def send_telegram_message(bot_token, chat_id, message):
    """Envia uma mensagem para um chat específico no Telegram."""
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para Telegram: {e}")
        return None


# ============ INTERFACE GRÁFICA ============ #
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bot BTC - Monitor em Tempo Real")
        self.geometry("1400x900")

        # Primeiro inicializamos todos os componentes da interface
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.stats_frame = tk.Frame(self, width=300, bg='#f0f0f0')
        self.stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Área de log deve ser criada antes de ser usada
        self.log_area = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, width=100, height=15)
        self.log_area.pack(pady=10, fill=tk.X)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self.main_frame, textvariable=self.status_var, font=("Arial", 12, "bold"))
        self.status_label.pack()

        # Gráfico
        self.fig, (self.ax, self.ax_rsi) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [2, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Inicializar componentes de estatísticas
        self.init_stats_panel()

        # Agora que todos os componentes estão criados, podemos enviar a mensagem
        self.enviar_mensagem_inicio()

        self.protocol("WM_DELETE_WINDOW", self.salvar_antes_de_sair)
        self.iniciar_thread()

    def enviar_mensagem_inicio(self):
        """Envia mensagem de inicialização para o Telegram"""
        try:
            startup_msg = f"🤖 BOT INICIADO\n\n" \
                          f"🔄 Par: {SYMBOL}\n" \
                          f"💰 Saldo Inicial: ${saldo_simulado:.2f}\n" \
                          f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n" \
                          f"⚙️ Configurações:\n" \
                          f"- Intervalo: {INTERVALO}s\n" \
                          f"- N: {N}\n" \
                          f"- Fator: {FATOR}\n" \
                          f"- Risco por operação: {RISCO_POR_OPERACAO_PERCENTUAL}%"
            send_telegram_message(BOT_TOKEN, CHAT_ID, startup_msg)
            self.log("Mensagem de inicialização enviada para o Telegram")
        except Exception as e:
            print(f"Erro ao enviar mensagem de início: {e}")

    def init_stats_panel(self):
        """Inicializa o painel de estatísticas"""
        tk.Label(self.stats_frame, text="ESTATÍSTICAS", font=("Arial", 12, "bold"), bg='#f0f0f0').pack(pady=10)

        # Métricas de desempenho
        self.metrics = {
            'saldo_total': tk.StringVar(value="💰 Saldo: $1000.00"),
            'lucro_total': tk.StringVar(value="📈 Lucro Total: $0.00"),
            'operacoes_hoje': tk.StringVar(value="📅 Operações Hoje: 0/100"),
            'posicoes_abertas': tk.StringVar(value="🔓 Posições Abertas: 0"),
            'win_rate': tk.StringVar(value="🎯 Win Rate: 0%"),
            'avg_win': tk.StringVar(value="⬆️ Avg Win: $0.00"),
            'avg_loss': tk.StringVar(value="⬇️ Avg Loss: $0.00"),
            'perda_diaria': tk.StringVar(value="⚠️ Perda Diária: $0.00 (0.00%)"),
            'rsi_atual': tk.StringVar(value="📊 RSI Atual: 0.00"),
            'preco_medio': tk.StringVar(value="⚖️ Preço Médio: $0.00"),
            'exposicao': tk.StringVar(value="📉 Exposição: $0.00 (0.00%)"),
            'status_bot': tk.StringVar(value="🔄 Status: ATIVO")
        }

        for metric, var in self.metrics.items():
            tk.Label(self.stats_frame, textvariable=var, anchor='w', bg='#f0f0f0').pack(fill=tk.X, padx=5, pady=2)

        # Botões de controle
        tk.Button(self.stats_frame, text="Exportar Dados", command=self.exportar_dados).pack(pady=10, fill=tk.X)
        tk.Button(self.stats_frame, text="Pausar Bot", command=self.toggle_pause).pack(pady=5, fill=tk.X)

        # Adicionar separador
        ttk.Separator(self.stats_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Configurações rápidas
        tk.Label(self.stats_frame, text="CONFIGURAÇÕES", font=("Arial", 10, "bold"), bg='#f0f0f0').pack()

        self.var_auto_export = tk.BooleanVar(value=True)
        tk.Checkbutton(self.stats_frame, text="Auto Exportar", variable=self.var_auto_export, bg='#f0f0f0').pack(
            anchor='w')

        # Histórico rápido
        self.history_list = tk.Listbox(self.stats_frame, height=8)
        self.history_list.pack(fill=tk.BOTH, expand=True, pady=5)

    def log(self, mensagem):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {mensagem}\n")
        self.log_area.see(tk.END)
        self.update_status()
        self.update_metrics()

    def update_status(self):
        status_text = f"💰 Saldo: ${saldo_simulado:.2f} | Operações Hoje: {operacoes_hoje}/{MAX_OPERACOES_POR_DIA}"
        if posicoes_abertas:
            status_text += f" | Posições Abertas: {len(posicoes_abertas)}"
        status_text += f" | Perda Diária: ${perda_diaria_acumulada:.2f}"
        self.status_var.set(status_text)

    def update_metrics(self):
        """Atualiza todas as métricas do painel de estatísticas"""
        # Calcular métricas básicas
        total_operacoes = len(historico_operacoes)
        operacoes_lucrativas = sum(1 for op in historico_operacoes if op['lucro'] > 0)
        win_rate = (operacoes_lucrativas / total_operacoes * 100) if total_operacoes > 0 else 0

        lucros = [op['lucro'] for op in historico_operacoes if op['lucro'] > 0]
        perdas = [abs(op['lucro']) for op in historico_operacoes if op['lucro'] < 0]

        avg_win = np.mean(lucros) if lucros else 0
        avg_loss = np.mean(perdas) if perdas else 0

        # Valor em posições abertas
        exposicao = sum(pos['qtd'] * pos['preco'] for pos in posicoes_abertas)
        exposicao_percent = (exposicao / saldo_simulado) * 100 if saldo_simulado > 0 else 0

        # Preço médio das posições abertas
        preco_medio = np.mean([pos['preco'] for pos in posicoes_abertas]) if posicoes_abertas else 0

        # Atualizar variáveis
        self.metrics['saldo_total'].set(f"💰 Saldo: ${saldo_simulado:.2f}")
        self.metrics['lucro_total'].set(f"📈 Lucro Total: ${saldo_simulado - 1000:.2f}")
        self.metrics['operacoes_hoje'].set(f"📅 Operações Hoje: {operacoes_hoje}/{MAX_OPERACOES_POR_DIA}")
        self.metrics['posicoes_abertas'].set(f"🔓 Posições Abertas: {len(posicoes_abertas)}")
        self.metrics['win_rate'].set(f"🎯 Win Rate: {win_rate:.1f}%")
        self.metrics['avg_win'].set(f"⬆️ Avg Win: ${avg_win:.2f}")
        self.metrics['avg_loss'].set(f"⬇️ Avg Loss: ${avg_loss:.2f}")
        self.metrics['perda_diaria'].set(
            f"⚠️ Perda Diária: ${perda_diaria_acumulada:.2f} ({perda_diaria_acumulada / saldo_simulado * 100:.2f}%)")
        self.metrics['rsi_atual'].set(f"📊 RSI Atual: {rsi_valores[-1]:.2f}" if rsi_valores else "📊 RSI Atual: -")
        self.metrics['preco_medio'].set(f"⚖️ Preço Médio: ${preco_medio:.2f}")
        self.metrics['exposicao'].set(f"📉 Exposição: ${exposicao:.2f} ({exposicao_percent:.2f}%)")

        # Atualizar histórico
        self.history_list.delete(0, tk.END)
        for op in historico_operacoes[-10:][::-1]:  # Mostrar as últimas 10 operações
            tipo = "LUCRO" if op['lucro'] > 0 else "PERDA"
            self.history_list.insert(0, f"{op['hora']} - {tipo}: ${abs(op['lucro']):.2f}")

    def atualizar_grafico(self):
        try:
            self.ax.clear()

            # Plotar preços
            self.ax.plot(precos[-100:], label='Preço BTC', color='blue', linewidth=2)

            # Adicionar bandas de Bollinger se tivermos dados suficientes
            if len(precos) >= N:
                bandas = self.calcular_bandas()
                self.ax.plot([bandas['media']] * len(precos[-100:]), linestyle='--', color='grey', label='MM20')
                self.ax.plot([bandas['superior']] * len(precos[-100:]), linestyle='--', color='red',
                             label='Banda Superior')
                self.ax.plot([bandas['inferior']] * len(precos[-100:]), linestyle='--', color='green',
                             label='Banda Inferior')

                # Preencher área entre as bandas
                self.ax.fill_between(range(len(precos[-100:])),
                                     [bandas['inferior']] * len(precos[-100:]),
                                     [bandas['superior']] * len(precos[-100:]),
                                     color='grey', alpha=0.1)

            # Adicionar marcadores para operações
            self.plotar_operacoes()

            # Configurações do gráfico
            self.ax.set_title("Preço do BTC em Tempo Real", fontsize=14)
            self.ax.legend(loc='upper left')
            self.ax.grid(True, linestyle='--', alpha=0.7)

            # Gráfico RSI
            self.ax_rsi.clear()
            if rsi_valores:
                self.ax_rsi.plot(rsi_valores[-100:], color='orange', label='RSI 14')
                self.ax_rsi.axhline(30, color='green', linestyle='--', alpha=0.7)
                self.ax_rsi.axhline(70, color='red', linestyle='--', alpha=0.7)
                self.ax_rsi.fill_between(range(len(rsi_valores[-100:])),
                                         rsi_valores[-100:], 30, where=(np.array(rsi_valores[-100:]) < 30),
                                         color='green', alpha=0.3)
                self.ax_rsi.fill_between(range(len(rsi_valores[-100:])),
                                         rsi_valores[-100:], 70, where=(np.array(rsi_valores[-100:]) > 70),
                                         color='red', alpha=0.3)
                self.ax_rsi.set_title("RSI 14 Períodos", fontsize=12)
                self.ax_rsi.set_ylim(0, 100)
                self.ax_rsi.grid(True, linestyle='--', alpha=0.7)

            self.canvas.draw()
            self.update_metrics()

        except Exception as e:
            self.log(f"Erro no gráfico: {str(e)}")

    def plotar_operacoes(self):
        """Adiciona marcadores para operações no gráfico"""
        if not historico_operacoes:
            return

        # Pegar apenas as operações que estão no intervalo visível
        ops_visiveis = [op for op in historico_operacoes if op['compra'] in precos[-100:]]

        for op in ops_visiveis:
            idx = precos[-100:].index(op['compra'])
            if op['lucro'] > 0:
                self.ax.plot(idx, op['compra'], 'g^', markersize=8)
                self.ax.plot(idx, op['venda'], 'gv', markersize=8)
            else:
                self.ax.plot(idx, op['compra'], 'r^', markersize=8)
                self.ax.plot(idx, op['venda'], 'rv', markersize=8)

    def calcular_bandas(self):
        media = np.mean(precos[-N:])
        std = np.std(precos[-N:])
        return {
            'media': media,
            'superior': media + FATOR * std,
            'inferior': media - FATOR * std
        }

    def exportar_dados(self):
        """Exporta dados para Excel"""
        try:
            # Salvar histórico de operações
            df_operacoes = pd.DataFrame(historico_operacoes)
            df_operacoes.to_excel("historico_operacoes.xlsx", index=False)

            # Salvar histórico de preços
            df_precos = pd.DataFrame({'Preço': precos, 'RSI': rsi_valores[:len(precos)]})
            df_precos.to_excel("historico_precos.xlsx", index=False)

            self.log("📊 Dados exportados para Excel")
        except Exception as e:
            self.log(f"Erro ao exportar dados: {str(e)}")

    def toggle_pause(self):
        """Pausa/despausa o bot"""
        global bot_pausado
        bot_pausado = not bot_pausado
        status = "PAUSADO" if bot_pausado else "ATIVO"
        self.log(f"Bot {status}")
        self.metrics['status_bot'].set(f"🔄 Status: {status}")

        # Enviar mensagem para Telegram
        msg = f"⏸️ Bot {status.lower()}" if bot_pausado else f"▶️ Bot {status.lower()}"
        send_telegram_message(BOT_TOKEN, CHAT_ID, msg)

    def salvar_transacoes_excel(self):
        try:
            df = pd.DataFrame(historico_operacoes)
            df.to_excel("transacoes_btc.xlsx", index=False)
            self.log("📁 Transações salvas em 'transacoes_btc.xlsx'")
        except Exception as e:
            self.log(f"Erro ao salvar Excel: {str(e)}")

    def salvar_antes_de_sair(self):
        self.salvar_transacoes_excel()

        # Enviar mensagem de encerramento
        shutdown_msg = f"🔴 BOT ENCERRADO\n\n" \
                       f"💰 Saldo Final: ${saldo_simulado:.2f}\n" \
                       f"📈 Lucro/Perda: ${saldo_simulado - 1000:.2f}\n" \
                       f"📅 Operações Hoje: {operacoes_hoje}\n" \
                       f"🕒 Hora: {datetime.now().strftime('%H:%M:%S')}"
        send_telegram_message(BOT_TOKEN, CHAT_ID, shutdown_msg)

        self.destroy()

    def registrar_preco(self, preco):
        """Registra o preço atual no log de preços"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            novo_registro = pd.DataFrame([[timestamp, preco]], columns=['timestamp', 'preco'])

            with open('precos_log.csv', 'a') as f:
                novo_registro.to_csv(f, header=False, index=False)
        except Exception as e:
            self.log(f"Erro ao registrar preço: {str(e)}")

    def registrar_operacao(self, tipo, preco_compra, preco_venda, quantidade):
        """Registra uma operação de compra/venda no log de operações"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            novo_registro = pd.DataFrame([[timestamp, tipo, preco_compra, preco_venda, quantidade, saldo_simulado]],
                                         columns=['hora', 'tipo', 'preco_compra', 'preco_venda', 'quantidade', 'saldo'])

            with open('operacoes_log.csv', 'a') as f:
                novo_registro.to_csv(f, header=False, index=False)
        except Exception as e:
            self.log(f"Erro ao registrar operação: {str(e)}")

    def iniciar_thread(self):
        def estrategia():
            global saldo_simulado, perda_diaria_acumulada, dia_atual, operacoes_hoje, bot_pausado

            while True:
                try:
                    if bot_pausado:
                        time.sleep(1)
                        continue

                    agora = datetime.now()
                    if agora.day != dia_atual:
                        dia_atual = agora.day
                        perda_diaria_acumulada = 0.0
                        operacoes_hoje = 0
                        self.after(0, self.log, "Novo dia de negociação, zerando perda diária e contador de operações.")

                        # Enviar mensagem de novo dia
                        msg = f"📅 NOVO DIA DE NEGOCIAÇÃO\n\n" \
                              f"💰 Saldo: ${saldo_simulado:.2f}\n" \
                              f"📊 Operações ontem: {len([op for op in historico_operacoes if datetime.strptime(op['hora'], '%Y-%m-%d %H:%M:%S').day == (agora.day - 1)])}"
                        send_telegram_message(BOT_TOKEN, CHAT_ID, msg)

                    if operacoes_hoje >= MAX_OPERACOES_POR_DIA:
                        self.after(0, self.log,
                                   f"Limite máximo de {MAX_OPERACOES_POR_DIA} operações para hoje atingido.")
                        time.sleep(INTERVALO)
                        continue

                    novo_preco = float(client.get_symbol_ticker(symbol=SYMBOL)['price'])
                    precos.append(novo_preco)
                    self.after(0, self.registrar_preco, novo_preco)

                    if len(precos) >= 15:
                        rsi_valores.append(RSIIndicator(pd.Series(precos), window=14).rsi().iloc[-1])
                        self.after(0, self.atualizar_grafico)

                    self.after(0, self.log, f"Preço atualizado: ${novo_preco:.2f}")

                    if len(precos) >= N:
                        bandas = self.calcular_bandas()
                        if novo_preco <= bandas['inferior'] and rsi_valores[-1] < 35:
                            if perda_diaria_acumulada < saldo_simulado * (PERDA_DIARIA_MAXIMA_PERCENTUAL / 100):
                                tamanho_posicao = calcular_tamanho_posicao(saldo_simulado,
                                                                           RISCO_POR_OPERACAO_PERCENTUAL, novo_preco)
                                valor_investimento = tamanho_posicao * novo_preco
                                if saldo_simulado >= valor_investimento:
                                    stop_loss_preco = novo_preco * (1 - (PERDA_POR_OPERACAO_PERCENTUAL / 100))
                                    nova_posicao = {
                                        'preco': novo_preco,
                                        'qtd': tamanho_posicao,
                                        'hora': time.time(),
                                        'stop_loss': stop_loss_preco
                                    }
                                    posicoes_abertas.append(nova_posicao)
                                    saldo_simulado -= valor_investimento
                                    mensagem_compra = f"🚀 COMPRA EXECUTADA:\nPar: {SYMBOL}\nPreço: ${novo_preco:.2f}\nQuantidade: {nova_posicao['qtd']:.6f} BTC\nStop Loss: ${stop_loss_preco:.2f}"
                                    send_telegram_message(BOT_TOKEN, CHAT_ID, mensagem_compra)
                                    self.after(0, self.log,
                                               f"COMPRA: {nova_posicao['qtd']:.6f} BTC @ ${novo_preco:.2f}, SL: ${stop_loss_preco:.2f}")
                                    self.after(0, self.registrar_operacao, 'COMPRA', novo_preco, None,
                                               nova_posicao['qtd'])
                                    operacoes_hoje += 1
                                else:
                                    self.after(0, self.log, "Saldo insuficiente para nova ordem.")
                            else:
                                self.after(0, self.log, "Limite de perda diária atingido. Negociações pausadas.")

                        for posicao in posicoes_abertas[:]:
                            # Verificar stop loss da posição
                            if novo_preco <= posicao['stop_loss']:
                                valor_venda = posicao['qtd'] * novo_preco
                                saldo_simulado += valor_venda
                                perda = (posicao['preco'] * posicao['qtd']) - valor_venda
                                perda_diaria_acumulada += perda
                                operacao = {
                                    'hora': time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'compra': posicao['preco'],
                                    'venda': novo_preco,
                                    'lucro': -perda
                                }
                                historico_operacoes.append(operacao)
                                mensagem_venda_sl = f"🚨 STOP LOSS ATIVADO:\nPar: {SYMBOL}\nPreço de Compra: ${posicao['preco']:.2f}\nPreço de Venda: ${novo_preco:.2f}\nQuantidade: {posicao['qtd']:.6f} BTC\nPERDA: ${perda:.2f}"
                                send_telegram_message(BOT_TOKEN, CHAT_ID, mensagem_venda_sl)
                                self.after(0, self.log,
                                           f"STOP LOSS ATIVADO! VENDA: Perda ${perda:.2f} @ ${novo_preco:.2f}")
                                self.after(0, self.registrar_operacao, 'VENDA', posicao['preco'], novo_preco,
                                           posicao['qtd'])
                                self.after(0, self.salvar_transacoes_excel)
                                posicoes_abertas.remove(posicao)
                                operacoes_hoje += 1
                                continue

                            lucro_atual_percentual = (novo_preco - posicao['preco']) / posicao['preco']
                            if lucro_atual_percentual >= 0.005:
                                valor_venda = posicao['qtd'] * novo_preco
                                saldo_simulado += valor_venda
                                lucro = valor_venda - (posicao['preco'] * posicao['qtd'])
                                operacao = {
                                    'hora': time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'compra': posicao['preco'],
                                    'venda': novo_preco,
                                    'lucro': lucro
                                }
                                historico_operacoes.append(operacao)
                                mensagem_venda_lucro = f"✅ VENDA COM LUCRO:\nPar: {SYMBOL}\nPreço de Compra: ${posicao['preco']:.2f}\nPreço de Venda: ${novo_preco:.2f}\nQuantidade: {posicao['qtd']:.6f} BTC\nLUCRO: ${lucro:.2f} ({lucro_atual_percentual:.2%})"
                                send_telegram_message(BOT_TOKEN, CHAT_ID, mensagem_venda_lucro)
                                self.after(0, self.log, f"VENDA: Lucro ${lucro:.2f} ({lucro_atual_percentual:.2%})")
                                self.after(0, self.registrar_operacao, 'VENDA', posicao['preco'], novo_preco,
                                           posicao['qtd'])
                                self.after(0, self.salvar_transacoes_excel)
                                posicoes_abertas.remove(posicao)
                                operacoes_hoje += 1

                    time.sleep(INTERVALO)

                except Exception as e:
                    mensagem_erro = f"⚠️ ERRO NO BOT:\n{str(e)}"
                    send_telegram_message(BOT_TOKEN, CHAT_ID, mensagem_erro)
                    self.after(0, self.log, f"ERRO: {str(e)}")
                    time.sleep(5)

        thread = threading.Thread(target=estrategia, daemon=True)
        thread.start()


if __name__ == "__main__":
    app = Application()
    app.mainloop()