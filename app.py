import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, auth

if not firebase_admin._apps:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    
from google.cloud import firestore

st.set_page_config(
    page_title="DashChamp",
    page_icon="⚽",
    layout="centered"
)

if st.query_params.get("tela") == "cadastro":
    st.session_state.tela = "cadastro"

# Autentica usando o mesmo JSON de serviço
db = firestore.Client.from_service_account_json('serviceAccountKey.json')

st.markdown(
    """
    <style>
        div.stButton > button {
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
            border: none;
            padding: 0.5rem 1.2rem;
            font-size: 16px;
            width: 200px;
            transition: background-color 0.2s ease, transform 0.2s ease;
        }

        div.stButton > button:hover {
            background-color: #2d792f;
            transform: translateY(-1px);
        }
    </style>
    """,
    unsafe_allow_html=True
)


if "tela" not in st.session_state:
    st.session_state.tela = "login"

def fazer_login(email, senha):
    api_key = "AIzaSyAm5WbhKJ47sOGcWRakVf03l_E2UKckrOM"

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword?key={api_key}"
    )

    dados = {
        "email": email,
        "password": senha,
        "returnSecureToken": True
    }

    resposta = requests.post(url, json=dados)

    return resposta

if st.session_state.tela == "login":

    with st.container(
        border=True,
        width=400,
        horizontal_alignment="center"
    ):

        st.title(":blue[Dash]:green[Champ]", text_alignment="center")

        email = st.text_input(
            "Email",
            placeholder="Digite seu email"
        )

        senha = st.text_input(
            "Senha",
            placeholder="Digite sua senha",
            type="password"
        )
        
        st.write(":blue[Esqueceu sua senha?]")
        
        
        st.markdown(
            'Não possui conta? <a href="?tela=cadastro">Cadastre-se</a>',
            unsafe_allow_html=True
        )
        
        if st.button("Entrar"):

            resposta = fazer_login(email, senha)

            if resposta.status_code == 200:
                dados_usuario = resposta.json()

                st.success("Login bem-sucedido!")

            else:
                st.error("Email ou senha incorretos.")


        # if st.button("Não possui conta?", width=200):
        #     st.session_state.tela = "cadastro"
        #     st.rerun()

        # st.button("Esqueceu sua senha?", width=200)


elif st.session_state.tela == "cadastro":

    with st.container(
        border=True,
        width=400,
        horizontal_alignment="center"
    ):

        st.title("Criar conta", text_alignment="center")
        
        usuario = st.text_input(
            "Usuário",
            placeholder="Digite seu usuário"
        )
        
        email = st.text_input(
            "Email",
            placeholder="Digite seu email"
        )

        senha = st.text_input(
            "Nova senha",
            placeholder="Digite sua senha",
            type="password"
        )

        confirmar_senha = st.text_input(
            "Confirmar senha",
            placeholder="Digite novamente sua senha",
            type="password"
        )
        
        if st.button("Cadastrar"):
            # Aqui você pode adicionar a lógica para criar a conta no Firebase
            if usuario and email and senha and confirmar_senha:
                if senha == confirmar_senha:
                    try:
                        user = auth.create_user(
                            email=email,
                            password=senha,
                            display_name=usuario
                        )
                        user.uid
                        st.success("Conta criada com sucesso!")
                        st.session_state.tela = "login"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")
                else:
                    st.error("As senhas não coincidem.")
            else:
                st.error("Por favor, preencha todos os campos.")
                


        st.markdown(
            'Já possui conta? <a href="?tela=login">Faça login</a>',
            unsafe_allow_html=True
        )