import sys, subprocess, time, threading
from datetime import datetime
import tkinter as tk

# --- GARANTIR MOTOR DA CORRETORA ---
try:
    from iqoptionapi.stable_api import IQ_Option
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "https://github.com/iqoptionapi/iqoptionapi/archive/refs/heads/master.zip"])
    from iqoptionapi.stable_api import IQ_Option


class FiuBotOraculo:
    def __init__(self, root):
        self.root = root
        self.root.title("FIU BOT - ORACULO EXTREMO VIP")
        self.root.geometry("420x720")
        self.root.configure(bg="#0A0A0A")

        self.rodando = False
        self.mensagens = []

        # --- UI DESIGN ---
        tk.Label(root, text="FIU BOT", font=("Impact", 45), fg="#FF0000", bg="#0A0A0A").pack(pady=10)
        tk.Label(root, text="ESTRATEGIA: ORACULO EXTREMO", font=("Arial", 10, "bold"), fg="#FFA500", bg="#0A0A0A").pack()

        self.status_var = tk.StringVar(value="STATUS: DESLIGADO")
        tk.Label(root, textvariable=self.status_var, fg="#00FF00", bg="#0A0A0A", font=("Arial", 11, "bold")).pack(pady=10)

        tk.Label(root, text="Escolha a Moeda:", fg="white", bg="#0A0A0A", font=("Arial", 9, "bold")).pack(pady=(5, 0))
        self.ativo_var = tk.StringVar(value="EURUSD-OTC")
        opcoes = ["EURUSD-OTC", "EURGBP-OTC", "USDJPY-OTC", "AUDCAD-OTC", "EURUSD", "EURGBP"]
        self.menu_ativo = tk.OptionMenu(root, self.ativo_var, *opcoes)
        self.menu_ativo.config(bg="#222", fg="white", font=("Arial", 11, "bold"), highlightthickness=0, width=15)
        self.menu_ativo.pack(pady=5)

        self.ent_email = tk.Entry(root, width=35, bg="#1A1A1A", fg="white", insertbackground="white", borderwidth=0, font=("Arial", 10))
        self.ent_email.insert(0, "E-mail da Corretora")
        self.ent_email.pack(pady=10)

        self.ent_pass = tk.Entry(root, width=35, bg="#1A1A1A", fg="white", show="*", insertbackground="white", borderwidth=0, font=("Arial", 10))
        self.ent_pass.pack(pady=5)

        self.btn = tk.Button(
            root,
            text="LIGAR MODO EXTREMO",
            bg="#FF0000",
            fg="white",
            font=("Arial", 14, "bold"),
            width=20,
            height=2,
            command=self.alternar,
            borderwidth=0,
        )
        self.btn.pack(pady=20)

        self.log_area = tk.Text(root, width=48, height=16, bg="black", fg="#00FF00", font=("Consolas", 9), state="disabled")
        self.log_area.pack(padx=15, pady=5)

        self.verificar_mensagens()

    # --- COMANDOS BLINDADOS (ANTI-TRAVAMENTO) ---
    def log(self, msg):
        hr = datetime.now().strftime("%H:%M:%S")
        self.mensagens.append(f"[{hr}] {msg}")

    def set_status(self, msg):
        self.root.after(0, self.status_var.set, msg)

    def parar_seguro(self):
        self.rodando = False
        self.root.after(0, self.btn.config, {"text": "LIGAR MODO EXTREMO", "bg": "#FF0000"})
        self.set_status("STATUS: DESLIGADO")
        self.root.after(0, self.menu_ativo.config, {"state": "normal"})

    def verificar_mensagens(self):
        while self.mensagens:
            mensagem = self.mensagens.pop(0)
            self.log_area.configure(state="normal")
            self.log_area.insert(tk.END, mensagem + "\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state="disabled")
        self.root.after(100, self.verificar_mensagens)

    def alternar(self):
        if not self.rodando:
            self.rodando = True
            self.btn.config(text="PARAR ROBO", bg="#444")
            self.set_status("STATUS: CONECTANDO...")
            self.menu_ativo.config(state="disabled")
            threading.Thread(target=self.motor_bot, args=(self.ent_email.get(), self.ent_pass.get()), daemon=True).start()
        else:
            self.parar_seguro()

    def calcular_oraculo_extremo(self, velas):
        if not velas or len(velas) < 15:
            return None
        try:
            fechamentos = [vela["close"] for vela in velas]

            fast_ma = fechamentos[-1]
            slow_ma = sum(fechamentos[-5:]) / 5
            diff_atual = fast_ma - slow_ma
            diff_anterior = fechamentos[-2] - (sum(fechamentos[-6:-1]) / 5)

            sig_atual = diff_atual * 0.5
            sig_anterior = diff_anterior * 0.5

            fluxo = sum((vela["close"] - vela["open"]) for vela in velas[-2:]) / 2

            if diff_anterior <= sig_anterior and diff_atual > sig_atual and fluxo > 0.00001:
                return "call"
            if diff_anterior >= sig_anterior and diff_atual < sig_atual and fluxo < -0.00001:
                return "put"
        except Exception:
            return None
        return None

    def reconectar_api(self, api):
        for tentativa in range(1, 4):
            if not self.rodando:
                return False
            self.log(f"Reconectando na corretora ({tentativa}/3)...")
            check, _ = api.connect()
            if check:
                self.log("Conexao restabelecida.")
                return True
            time.sleep(2)
        self.log("Ainda sem conexao. Vou continuar tentando sem desligar o bot.")
        return False

    def aguardar_resultado(self, api, id_ordem, timeout=25):
        inicio = time.time()
        while self.rodando and (time.time() - inicio) < timeout:
            try:
                if not api.check_connect() and not self.reconectar_api(api):
                    time.sleep(2)
                    continue

                resultado = api.check_win_v4(id_ordem)
                if resultado is None:
                    time.sleep(1)
                    continue

                return float(resultado)
            except Exception:
                time.sleep(1)

        self.log("Resultado demorou demais. Vou soltar a operacao e continuar procurando sinais.")
        return None

    def executar_operacao(self, api, ativo, sinal):
        valor = 10.0

        for gale in range(3):
            if not self.rodando:
                return

            fase = "ENTRADA" if gale == 0 else f"GALE {gale}"
            self.log(f"{fase} (R${valor:.2f})...")

            ok, id_ordem = api.buy(valor, ativo, sinal, 1)
            if not ok:
                self.log("Corretora recusou a ordem (bloqueio, mercado fechado ou limite).")
                return

            self.log("Ordem enviada. Aguardando fechamento da vela...")
            for restante in range(50, 0, -10):
                if not self.rodando:
                    return
                self.set_status(f"OPERACAO ROLANDO... {restante}s")
                time.sleep(10)

            self.set_status("CHECANDO RESULTADO...")
            resultado = self.aguardar_resultado(api, id_ordem)
            if resultado is None:
                self.set_status(f"CACANDO SINAIS: {ativo}")
                return

            if resultado > 0:
                self.log(f"WIN! Lucro: +R${resultado:.2f}")
                self.set_status(f"CACANDO SINAIS: {ativo}")
                return

            self.log(f"LOSS (R${resultado:.2f}). Preparando proximo gale...")
            valor = round(valor * 2.3, 2)

        self.set_status(f"CACANDO SINAIS: {ativo}")

    def motor_bot(self, email, senha):
        api = IQ_Option(email, senha)
        check, _ = api.connect()
        if not check:
            self.log("Erro de login. Verifique os dados.")
            self.parar_seguro()
            return

        api.change_balance("PRACTICE")
        ativo = self.ativo_var.get()
        self.log(f"Conectado. Camera rapida ligada no {ativo}.")
        self.set_status(f"CACANDO SINAIS: {ativo}")

        ultima_vela_id = None
        proximo_log = 0

        while self.rodando:
            try:
                if not api.check_connect():
                    self.log("Queda silenciosa detectada na corretora.")
                    self.set_status("RECONECTANDO...")
                    if not self.reconectar_api(api):
                        time.sleep(2)
                    continue

                agora_ts = int(time.time())
                segundo = datetime.now().second

                if agora_ts >= proximo_log:
                    self.log(f"Analisando micro-tendencias do {ativo}...")
                    proximo_log = agora_ts + 10

                if segundo >= 58:
                    velas = api.get_candles(ativo, 60, 20, agora_ts)
                    if velas:
                        sinal = self.calcular_oraculo_extremo(velas)
                        vela_id = velas[-1]["id"]

                        if sinal and vela_id != ultima_vela_id:
                            ultima_vela_id = vela_id
                            direcao = "COMPRA (CALL)" if sinal == "call" else "VENDA (PUT)"
                            self.log(f"SINAL EXTREMO: {direcao}")
                            self.executar_operacao(api, ativo, sinal)
                        elif vela_id != ultima_vela_id:
                            ultima_vela_id = vela_id
                            self.log("Sem sinal valido nesta virada. Continuando...")

                    self.set_status(f"CACANDO SINAIS: {ativo}")
                    time.sleep(2)

                time.sleep(0.5)

            except Exception:
                self.log("Erro de rede ou resposta invalida. Vou continuar tentando automaticamente.")
                self.set_status(f"CACANDO SINAIS: {ativo}")
                time.sleep(2)


if __name__ == "__main__":
    root = tk.Tk()
    FiuBotOraculo(root)
    root.mainloop()
