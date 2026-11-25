import firebase_admin
from firebase_admin import auth, credentials, firestore


def salvar_usuario(db, usuario):
    dados = {}

    if usuario.display_name is not None:
        dados["nome"] = usuario.display_name
    if usuario.email is not None:
        dados["email"] = usuario.email

    db.collection("usuarios").document(usuario.uid).set(dados, merge=True)


if __name__ == "__main__":
    firebase_admin.initialize_app(
        credentials.Certificate("serviceAccountKey.json")
    )
    db = firestore.client()

    total = 0
    for usuario in auth.list_users().iterate_all():
        salvar_usuario(db, usuario)
        total += 1

    print(f"{total} usuários sincronizados com o Firestore.")