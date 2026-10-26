import streamlit as st

st.title("Salas")
st.write("Crie uma sala ou entre em uma sala existente.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Criar sala")
    
    nome_sala = st.text_input("Nome da sala", key="nome_sala")
    
    max_jogadores = st.number_input(
        "Número máximo de jogadores", 
        min_value=1, 
        max_value=100, 
        value=10, 
        step=1,
        key="max_jogadores"
    )
    
    rodada_campeonato = st.number_input(
        "Rodada do campeonato", 
        min_value=1, 
        max_value=50, 
        value=1, 
        step=1,
        key="rodada_campeonato"
    )
    
    if st.button("Criar sala", type="primary", use_container_width=True):
        if nome_sala.strip():
            st.success(f"Sala '{nome_sala}' criada com sucesso!")
        else:
            st.error("Por favor, digite o nome da sala.")

    if st.button("Voltar", use_container_width=True):
        # Redireciona de volta para a Home
        st.session_state.tela = 'menu'
        st.rerun()

with col2:
    st.subheader("Entrar em uma sala")
    
    codigo_sala = st.text_input("Código da sala", key="codigo_sala")
    
    if st.button("Entrar", type="primary", use_container_width=True):
        if codigo_sala.strip():
            st.success(f"Entrando na sala {codigo_sala}...")
        else:
            st.error("Por favor, digite o código da sala.")