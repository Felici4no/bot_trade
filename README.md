# 🤖 Bot de Trading Automatizado para Bitcoin (BTC/USDT)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

Bot de trading automatizado para Bitcoin utilizando uma estratégia híbrida baseada em **Bollinger Bands** e **RSI**, com interface gráfica em tempo real e integração com **Telegram** para notificações.

---

## 🚀 Funcionalidades Principais

- **📈 Estratégia Híbrida**:
  - Bollinger Bands (N=20, Fator=2.5)
  - RSI (14 períodos)
- **🖥️ Interface Gráfica em Tempo Real**:
  - Gráfico de preços com bandas de Bollinger
  - Gráfico de RSI com zonas de sobrecompra/sobrevenda
  - Painel com estatísticas detalhadas
- **🛡️ Gestão de Risco Avançada**:
  - Stop loss por operação (0.5%)
  - Limite diário de operações (100)
  - Perda máxima diária (2%)
- **📲 Integração com Telegram**:
  - Alertas de compra e venda
  - Notificações de erro
  - Relatórios diários automatizados
- **📊 Registro de Operações**:
  - Logs em CSV e Excel
  - Histórico completo de transações

---

## ⚙️ Instalação

### 1. Pré-requisitos

```bash
Python 3.8+
pip install -r requirements.txt
````

**Arquivo `requirements.txt`:**

```
binance-connector
pandas
numpy
matplotlib
tk
ta
python-telegram-bot
requests
```

### 2. Configuração das Chaves de API

Edite o código com suas credenciais:

```python
API_KEY = "sua_api_key_da_Binance"
API_SECRET = "seu_secret_da_Binance"
BOT_TOKEN = "seu_token_do_bot_do_Telegram"
CHAT_ID = "seu_chat_id_do_Telegram"
```

---

## 📊 Como Usar

Execute o bot:

```bash
python bot_btc.py
```

A interface gráfica exibe:

* Gráfico de preços ao vivo
* Painel de controle com:

  * Status atual do bot
  * Métricas de desempenho
  * Histórico de operações
  * Controles de pausa e exportação

---

## ⚠️ Parâmetros de Gestão de Risco

Você pode ajustar os parâmetros diretamente no código:

```python
PERDA_POR_OPERACAO_PERCENTUAL = 0.5       # 0.5% por operação
RISCO_POR_OPERACAO_PERCENTUAL = 1.0       # 1% do saldo
PERDA_DIARIA_MAXIMA_PERCENTUAL = 2.0      # 2% perda máxima diária
MAX_OPERACOES_POR_DIA = 100               # 100 operações por dia
```

---

## 📈 Estratégia de Trading

### 🟢 Sinal de Compra:

* Preço toca a banda inferior de Bollinger
* RSI < 35
* Dentro dos parâmetros de risco

### 🔴 Sinal de Venda:

* **Take Profit**: Lucro de 0.5%
* **Stop Loss**: Prejuízo de 0.5%

---

## 📁 Estrutura de Arquivos

* `precos_log.csv` — Histórico de preços
* `operacoes_log.csv` — Registro de operações executadas
* `transacoes_btc.xlsx` — Exportação completa das transações

---

## 📬 Notificações via Telegram

**Exemplos de mensagens enviadas:**

```
🚀 COMPRA EXECUTADA:
Par: BTCUSDT
Preço: $50,000.00
Quantidade: 0.002000 BTC
Stop Loss: $49,750.00

🚨 STOP LOSS ATIVADO:
Perda: $25.00
```

---

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).

---

## ⚠️ Aviso Importante

> **Este é um projeto educacional**. Use por sua conta e risco. Recomendamos:
>
> * Testar exaustivamente em conta demo
> * Ajustar parâmetros ao seu perfil
> * Não utilizar com capital real sem conhecimento dos riscos envolvidos


