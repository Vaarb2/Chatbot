import customtkinter as ctk
import spacy
import pandas as pd
import gspread
from fuzzywuzzy import process
from oauth2client.service_account import ServiceAccountCredentials

# Configuração para acessar o Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gc = gspread.authorize(credentials)
sheet_url = "https://docs.google.com/spreadsheets/d/1H3r7baTG-wt-vbJf6iCtv8UArkAyRL6KKUuo4zQqSI4/edit#gid=1580983498"
sheet = gc.open_by_url(sheet_url).sheet1

data = pd.DataFrame(sheet.get_all_records())

# Carregar o modelo de português
nlp = spacy.load('pt_core_news_sm')

# Dicionário de palavras-chave
KEYWORDS = {
    "bairro": ["bairro", "localidade", "região", "zona"],
    "situação": ["situação", "status", "condição"]
}

class Chatbot:
    def __init__(self, master):
        self.master = master
        master.title("Artemis")
        master.geometry("600x500")

        # Configuração da janela
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=0)
        master.grid_rowconfigure(2, weight=0)

        ctk.set_appearance_mode("dark")  # "light" ou "dark"
        ctk.set_default_color_theme("dark-blue")

        # Área de texto
        self.text_area = ctk.CTkTextbox(master, width=500, height=300, wrap="word")
        self.text_area.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.text_area.insert(ctk.END, "Olá! Eu sou a Artemis, sua assistente virtual. Como posso te ajudar hoje?\n")
        self.text_area.configure(state="disabled")

        # Campo de entrada
        self.entry = ctk.CTkEntry(master, width=400, placeholder_text="Digite sua pergunta aqui...")
        self.entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.entry.bind("<Return>", self.process_input)

        # Botão de envio
        self.send_button = ctk.CTkButton(master, text="Enviar", fg_color="blue", command=self.process_input)
        self.send_button.grid(row=2, column=0, padx=20, pady=10)

    def process_input(self, event=None):
        user_input = self.entry.get()
        if not user_input:
            return

        self.text_area.configure(state="normal")
        self.text_area.insert(ctk.END, "Você: " + user_input + "\n")

        response = self.get_bot_response(user_input)
        self.text_area.insert(ctk.END, "Artemis: " + response + "\n")

        self.text_area.configure(state="disabled")
        self.entry.delete(0, ctk.END)

    def get_bot_response(self, user_input):
        # Processar o input com spaCy
        doc = nlp(user_input.lower())
        tokens = [token.lemma_ for token in doc if not token.is_punct and not token.is_stop]

        # Identificar a intenção
        intent = self.identify_intent(tokens)
        if intent == "bairro":
            bairro = self.extract_entity(doc, "bairro")
            if bairro:
                return self.get_data_by_bairro(bairro)
            return "Por favor, informe o bairro desejado."

        elif intent == "situação":
            situacao = self.extract_entity(doc, "situação")
            if situacao:
                return self.get_data_by_situacao(situacao)
            return "Por favor, informe a situação desejada."

        return "Desculpe, não entendi. Poderia reformular a pergunta?"

    def identify_intent(self, tokens):
        for token in tokens:
            for key, words in KEYWORDS.items():
                if token in words:
                    return key
        return None

    def get_data_by_bairro(self, bairro):
        bairro = self.find_closest_match(bairro, data['BAIRRO'].unique())
        if not bairro:
            return f"Não foram encontrados dados para o bairro especificado."

        filtered_data = data[data['BAIRRO'].str.contains(bairro, case=False, na=False)]
        if filtered_data.empty:
            return f"Não foram encontrados dados para o bairro '{bairro}'."

        return (f"Dados encontrados para o bairro '{bairro}':\n" +
                filtered_data[['SERVICO_DESCRICAO', 'SITUACAO']]
                .to_string(index=False))

    def get_data_by_situacao(self, situacao):
        situacao = self.find_closest_match(situacao, data['SITUACAO'].unique())
        if not situacao:
            return f"Não foram encontrados dados para a situação especificada."

        filtered_data = data[data['SITUACAO'].str.contains(situacao, case=False, na=False)]
        if filtered_data.empty:
            return f"Não foram encontrados dados para a situação '{situacao}'."

        return (f"Dados encontrados para a situação '{situacao}':\n" +
                filtered_data[['SERVICO_DESCRICAO', 'BAIRRO']]
                .to_string(index=False))

    def extract_entity(self, doc, entity_type):
        for token in doc:
            if token.text.lower() in KEYWORDS[entity_type]:
                idx = [t.i for t in doc].index(token.i)
                if idx + 1 < len(doc):
                    return doc[idx + 1].text
        return None

    def find_closest_match(self, query, choices):
        match, score = process.extractOne(query, choices)
        return match if score > 80 else None

if __name__ == "__main__":
    root = ctk.CTk()
    chatbot = Chatbot(root)
    root.mainloop()

