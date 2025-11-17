import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
import os
import subprocess
from datetime import datetime
from PIL import Image, ImageTk
import re
import sys
import hashlib
import unicodedata

# --- VARIÁVEIS GLOBAIS ---
df_global = None # DataFrame em memória para acesso rápido

def get_filename_for_tipologia(tipologia):
    """Gera um nome de arquivo padronizado para uma dada tipologia."""
    # Remove acentos, troca espaços por underscore e converte para minúsculas
    normalized = unicodedata.normalize('NFKD', tipologia)
    ascii_only = normalized.encode('ASCII', 'ignore').decode('ASCII')
    safe_name = ascii_only.lower().replace(' ', '_')
    return f'biblioteca_{safe_name}.xlsx'

# --- FUNÇÕES ---
def _license_file_path():
    base = os.getenv('APPDATA') or os.path.expanduser('~')
    folder = os.path.join(base, 'BibliotecaApp')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'license.dat')

def _license_valid():
    path = _license_file_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content == hashlib.sha256(b'1480').hexdigest()
    except Exception:
        return False

def _normalize_numero_value(val):
    """Normaliza o valor do campo 'Número':
    - se for inteiro, retorna int
    - se for decimal, retorna float
    - se não for número, retorna string original
    """
    s = str(val).strip().replace(',', '.')
    if s == "":
        return ""
    try:
        f = float(s)
        if f.is_integer():
            return int(f)
        return f
    except Exception:
        return val

def _format_numero_for_display(val):
    """Formata para exibição na tabela: inteiros sem casas, decimais com ponto ou vírgula do arquivo."""
    try:
        s = str(val).strip()
        if s == "":
            return ""
        f = float(s.replace(',', '.'))
        if f.is_integer():
            return str(int(f))
        return str(f)
    except Exception:
        return str(val)

def _request_activation(parent):
    for _ in range(3):
        pwd = simpledialog.askstring('Ativação', 'Digite a senha para ativar:', show='*', parent=parent)
        if pwd is None:
            break
        if hashlib.sha256(pwd.encode('utf-8')).hexdigest() == hashlib.sha256(b'1480').hexdigest():
            try:
                with open(_license_file_path(), 'w', encoding='utf-8') as f:
                    f.write(hashlib.sha256(b'1480').hexdigest())
            except Exception:
                pass
            return True
        else:
            messagebox.showerror('Erro', 'Senha incorreta.', parent=parent)
    messagebox.showinfo('Saindo', 'Ativação não concluída.')
    try:
        parent.destroy()
    except Exception:
        pass
    sys.exit(0)
def inicializar_dados():
    """Função mantida por compatibilidade, mas a carga de dados agora é feita sob demanda na aba de pesquisa."""
    global df_global
    df_global = pd.DataFrame(columns=all_columns)
    pass

def validar_data(data_str):
    if not data_str:
        return True
    s = str(data_str).strip()
    # Exige exatamente DD/MM/AAAA com dois dígitos para dia e mês
    if not re.match(r'^(0[1-9]|[12][0-9]|3[01])\/(0[1-9]|1[0-2])\/[0-9]{4}$', s):
        return False
    try:
        # Validação de calendário (ex.: rejeita 31/02/2024)
        datetime.strptime(s, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def salvar_dados(tipologia, entries, obs_text):
    """Coleta, valida e salva os dados em sua respectiva planilha de tipologia."""
    dados = {entry['label']: entry['widget'].get() for entry in entries}
    dados['Tipologia'] = tipologia
    dados['Observação'] = obs_text.get("1.0", tk.END).strip()

    if not dados.get('Título'):
        messagebox.showwarning("Atenção", "Os campos 'Registro' e 'Título' são obrigatórios.")
        return

    if not validar_data(dados.get('Data')):
        messagebox.showwarning("Atenção", "Formato de data inválido. Use DD/MM/AAAA.")
        return

    # Normaliza campo 'Número' antes de salvar
    if 'Número' in dados:
        dados['Número'] = _normalize_numero_value(dados.get('Número', ''))

    filename = get_filename_for_tipologia(tipologia)
    df_local = pd.DataFrame(columns=all_columns)
    if os.path.exists(filename):
        df_local = pd.read_excel(filename, dtype={'Registro': str})
        # Garante que todas as colunas existam
        for col in all_columns:
            if col not in df_local.columns:
                df_local[col] = ""

    # --- Numeração sequencial por Tipologia para 'Registro' ---
    def _parse_registro_numeric(s):
        try:
            return int(str(s)) if str(s).isdigit() else None
        except Exception:
            return None
    existentes_nums = [n for n in ( _parse_registro_numeric(v) for v in (df_local['Registro'].tolist() if 'Registro' in df_local.columns else []) ) if n is not None]
    atual_max = max(existentes_nums) if existentes_nums else 0
    proximo_num = atual_max + 1
    # Largura mínima 5; aumenta conforme necessário
    largura_existente = max([len(str(x)) for x in existentes_nums], default=0)
    largura = max(5, largura_existente, len(str(proximo_num)))
    registro_sequencial = str(proximo_num).zfill(largura)

    # Validação da entrada do usuário e padronização
    reg_usuario = str(dados.get('Registro', '')).strip()
    if not reg_usuario.isdigit() or reg_usuario != registro_sequencial:
        # Força o próximo sequencial e informa o usuário
        dados['Registro'] = registro_sequencial
    else:
        # Mesmo se o usuário acertar, normaliza zero-padding conforme largura calculada
        dados['Registro'] = str(int(reg_usuario)).zfill(largura)

    if 'Registro' in df_local.columns and not df_local.empty:
        registros_existentes = df_local['Registro'].astype(str).tolist()
        if dados['Registro'] in registros_existentes:
            messagebox.showerror("Erro", f"O Registro '{dados['Registro']}' já existe na planilha {filename}!")
            return

    try:
        novo_registro = pd.DataFrame([dados])
        # Garante que o novo registro tenha todas as colunas
        for col in all_columns:
            if col not in novo_registro.columns:
                novo_registro[col] = ""
        df_local = pd.concat([df_local, novo_registro], ignore_index=True)
        # Reordena colunas antes de salvar
        df_local = df_local[all_columns]
        # Garante que 'Registro' seja texto para preservar zeros à esquerda no Excel
        if 'Registro' in df_local.columns:
            df_local['Registro'] = df_local['Registro'].astype(str)
        df_local.to_excel(filename, index=False)
        messagebox.showinfo("Sucesso", "Dados salvos com sucesso!")
        # Limpa os campos após salvar com sucesso
        limpar_campos(entries, obs_text)
        # Atualiza a visualização na aba de pesquisa
        atualizar_visualizacao_pesquisa()
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar os dados.\nVerifique se o arquivo Excel não está aberto.\n\nErro: {e}")

def limpar_campos(entries, obs_text):
    for entry in entries:
        entry['widget'].delete(0, tk.END)
    obs_text.delete("1.0", tk.END)

def abrir_planilha_geral():
    """Salva o DataFrame global consolidado em um único arquivo Excel e o abre."""
    global df_global
    if df_global is None or df_global.empty:
        messagebox.showwarning("Atenção", "Não há dados para exportar. Realize uma pesquisa ou clique em 'Mostrar Todos' primeiro.")
        return

    filename = "biblioteca_geral.xlsx"
    try:
        # Garante que todos os campos existam e estejam na ordem padronizada
        df_export = df_global.copy()
        for col in all_columns:
            if col not in df_export.columns:
                df_export[col] = ""
        df_export = df_export[all_columns]
        # Garante que 'Registro' seja texto para preservar zeros
        if 'Registro' in df_export.columns:
            df_export['Registro'] = df_export['Registro'].astype(str)
        df_export.to_excel(filename, index=False)
        messagebox.showinfo("Sucesso", f"Planilha geral '{filename}' criada com sucesso!")
        if os.name == 'nt': os.startfile(filename)
        else: subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', filename))
    except Exception as e:
        messagebox.showerror("Erro ao Gerar Planilha", f"Não foi possível criar ou abrir a planilha geral.\n\nErro: {e}")

def abrir_planilha():
    """Abre a planilha correspondente à aba ativa."""
    try:
        selected_tab_index = tab_control.index(tab_control.select())
        tipologia_ativa = tab_control.tab(selected_tab_index, 'text')
        
        # Não faz sentido abrir planilha para a aba de pesquisa
        if tipologia_ativa == 'Pesquisar Tudo':
            messagebox.showinfo("Informação", "Selecione uma aba de cadastro (Livro, Folhetos, etc.) para ver a planilha correspondente.")
            return

        filename = get_filename_for_tipologia(tipologia_ativa)

        if not os.path.exists(filename):
            messagebox.showwarning("Atenção", f"Nenhum dado foi salvo para '{tipologia_ativa}' ainda. O arquivo '{filename}' não existe.")
            return
        # Normaliza a estrutura da planilha para conter todas as colunas (inclui 'Número') na ordem correta
        try:
            df_local_open = pd.read_excel(filename)
            changed = False
            for col in all_columns:
                if col not in df_local_open.columns:
                    df_local_open[col] = ""
                    changed = True
            # Reordena colunas se necessário
            if list(df_local_open.columns) != all_columns:
                df_local_open = df_local_open[all_columns]
                changed = True
            if changed:
                df_local_open.to_excel(filename, index=False)
        except Exception as e:
            print(f"AVISO: Falha ao normalizar planilha '{filename}': {e}")

        if os.name == 'nt': os.startfile(filename)
        else: subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', filename))
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

def normalizar_planilhas_existentes():
    """Garante que todos os arquivos de cada tipologia tenham as colunas 'all_columns' na ordem correta.
    Não cria arquivos novos; apenas ajusta os que existirem.
    """
    try:
        for tip in tipologias:
            filename = get_filename_for_tipologia(tip)
            if not os.path.exists(filename):
                continue
            try:
                df_local = pd.read_excel(filename, dtype={'Registro': str})
                changed = False
                for col in all_columns:
                    if col not in df_local.columns:
                        df_local[col] = ""
                        changed = True
                # Reordena colunas se necessário
                if list(df_local.columns) != all_columns:
                    df_local = df_local[all_columns]
                    changed = True
                # Garante tipo texto em Registro
                if 'Registro' in df_local.columns:
                    df_local['Registro'] = df_local['Registro'].astype(str)
                if changed:
                    df_local.to_excel(filename, index=False)
            except Exception as e:
                print(f"AVISO: Falha ao normalizar '{filename}': {e}")
    except Exception as e:
        print(f"AVISO: Erro geral na normalização: {e}")

def atualizar_visualizacao_pesquisa(df_filtrado=None):
    """Carrega todos os dados de todas as planilhas, os combina e exibe na tabela."""
    global df_global
    
    # Se um DataFrame filtrado for fornecido, use-o. Caso contrário, recarregue tudo.
    if df_filtrado is None:
        todos_os_dfs = []
        for tipologia in tipologias:
            filename = get_filename_for_tipologia(tipologia)
            if os.path.exists(filename):
                try:
                    df_temp = pd.read_excel(filename, dtype={'Registro': str})
                    # Garante que todas as colunas existam e ordem padronizada
                    for col in all_columns:
                        if col not in df_temp.columns:
                            df_temp[col] = ""
                    df_temp = df_temp[all_columns]
                    todos_os_dfs.append(df_temp)
                except Exception as e:
                    print(f"Erro ao ler {filename}: {e}")
        
        if todos_os_dfs:
            df_global = pd.concat(todos_os_dfs, ignore_index=True)
            # Reforça ordenação das colunas
            df_global = df_global[all_columns]
        else:
            df_global = pd.DataFrame(columns=all_columns)

    # Limpa a visualização antiga
    for item in result_tree.get_children():
        result_tree.delete(item)

    df_para_mostrar = df_filtrado if df_filtrado is not None else df_global
    # Garante que todas as colunas existam e na ordem correta, mesmo em arquivos antigos sem 'Número'
    if df_para_mostrar is not None and not df_para_mostrar.empty:
        for col in all_columns:
            if col not in df_para_mostrar.columns:
                df_para_mostrar[col] = ""
        df_para_mostrar = df_para_mostrar[all_columns]
    
    if df_para_mostrar is not None and not df_para_mostrar.empty:
        # Evita exibir 'nan' e formata 'Número' para inteiros quando aplicável
        df_temp = df_para_mostrar.copy()
        if 'Número' in df_temp.columns:
            df_temp['Número'] = df_temp['Número'].apply(_format_numero_for_display)
        df_temp = df_temp.fillna("").astype(str)
        for index, row in df_temp.iterrows():
            result_tree.insert('', tk.END, values=list(row))

def buscar_registro():
    """Filtra o DataFrame em memória e atualiza a visualização."""
    termo_busca = search_entry.get().strip().lower()
    if not termo_busca:
        atualizar_visualizacao_pesquisa()
        return
    if df_global is None or df_global.empty: return
    # Filtra por Registro, Autor ou Título
    registro_match = df_global['Registro'].fillna("").astype(str).str.lower().str.contains(termo_busca, na=False)
    autor_match = df_global['Autor'].fillna("").astype(str).str.lower().str.contains(termo_busca, na=False)
    titulo_match = df_global['Título'].fillna("").astype(str).str.lower().str.contains(termo_busca, na=False)
    df_filtrado = df_global[registro_match | autor_match | titulo_match]
    atualizar_visualizacao_pesquisa(df_filtrado)

def excluir_registro():
    """Exclui o registro selecionado do arquivo de planilha correto."""
    selected_item = result_tree.focus()
    if not selected_item:
        messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
        return

    item_values = result_tree.item(selected_item, 'values')
    # Identifica o registro e a tipologia pelas colunas correspondentes
    registro_para_excluir = item_values[all_columns.index('Registro')]
    tipologia_do_registro = item_values[all_columns.index('Tipologia')]
    autor = item_values[all_columns.index('Autor')]

    confirm = messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o registro?\n\nRegistro: {registro_para_excluir}\nAutor: {autor}\nTipologia: {tipologia_do_registro}")
    if confirm:
        filename = get_filename_for_tipologia(tipologia_do_registro)
        if not os.path.exists(filename):
            messagebox.showerror("Erro", f"Arquivo de origem '{filename}' não encontrado!")
            return
        
        try:
            df_local = pd.read_excel(filename, dtype={'Registro': str})
            df_local = df_local[df_local['Registro'].astype(str) != str(registro_para_excluir)]
            df_local.to_excel(filename, index=False)
            messagebox.showinfo("Sucesso", "Registro excluído com sucesso.")
            # Recarrega a visualização da pesquisa para refletir a exclusão
            atualizar_visualizacao_pesquisa()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar as alterações no arquivo '{filename}'.\n\nErro: {e}")

def editar_registro():
    """Abre uma nova janela para editar o registro selecionado."""
    selected_item = result_tree.focus()
    if not selected_item:
        messagebox.showwarning("Atenção", "Selecione um registro para editar.")
        return

    item_values = {all_columns[i]: result_tree.item(selected_item, 'values')[i] for i in range(len(all_columns))}

    edit_window = tk.Toplevel(app)
    edit_window.title("Editar Registro")
    edit_window.geometry("700x600")

    edit_entries = []
    # Exibe 'Registro' como somente leitura para manter a sequência
    i = 0
    for key, value in item_values.items():
        if key == 'Registro':
            label = ttk.Label(edit_window, text=f"{key}:")
            label.grid(row=i // 2, column=(i % 2) * 2, padx=10, pady=5, sticky='w')
            value_label = ttk.Label(edit_window, text=value)
            value_label.grid(row=i // 2, column=(i % 2) * 2 + 1, padx=10, pady=5, sticky='w')
            i += 1
            continue
        if key not in ['Tipologia', 'Observação']:
            label = ttk.Label(edit_window, text=f"{key}:")
            label.grid(row=i // 2, column=(i % 2) * 2, padx=10, pady=5, sticky='w')
            entry = ttk.Entry(edit_window, width=40)
            entry.grid(row=i // 2, column=(i % 2) * 2 + 1, padx=10, pady=5, sticky='ew')
            entry.insert(0, value)
            edit_entries.append({'label': key, 'widget': entry})
            i += 1
    
    edit_window.grid_columnconfigure(1, weight=1)
    edit_window.grid_columnconfigure(3, weight=1)

    # Tipologia e Observação
    tipologia_label = ttk.Label(edit_window, text="Tipologia:")
    tipologia_label.grid(row=len(campos_registro)//2 + 1, column=0, padx=10, pady=5, sticky='w')
    edit_tipologia_var = tk.StringVar(value=item_values.get('Tipologia'))
    edit_tipologia_menu = ttk.OptionMenu(edit_window, edit_tipologia_var, item_values.get('Tipologia'), *tipologias)
    edit_tipologia_menu.grid(row=len(campos_registro)//2 + 1, column=1, padx=10, pady=5, sticky='w')

    obs_label = ttk.Label(edit_window, text="Observação:")
    obs_label.grid(row=len(campos_registro)//2 + 2, column=0, padx=10, pady=5, sticky='nw')
    edit_obs_text = tk.Text(edit_window, height=5)
    edit_obs_text.grid(row=len(campos_registro)//2 + 2, column=1, columnspan=3, padx=10, pady=5, sticky='ew')
    edit_obs_text.insert("1.0", item_values.get('Observação'))

    def salvar_edicao():
        novos_dados = {e['label']: e['widget'].get() for e in edit_entries}
        novos_dados['Tipologia'] = edit_tipologia_var.get()
        novos_dados['Observação'] = edit_obs_text.get("1.0", tk.END).strip()
        # Validação de data com formato DD/MM/AAAA
        if not validar_data(novos_dados.get('Data')):
            messagebox.showwarning("Atenção", "Formato de data inválido. Use DD/MM/AAAA.", parent=edit_window)
            return

        # Normaliza campo 'Número'
        if 'Número' in novos_dados:
            novos_dados['Número'] = _normalize_numero_value(novos_dados.get('Número', ''))

        original_registro = item_values.get('Registro')
        original_tipologia = item_values.get('Tipologia')
        # Registro não é editável: mantém o original
        novo_registro = original_registro
        nova_tipologia = novos_dados['Tipologia']

        try:
            # Carrega e normaliza o arquivo de origem (onde o registro foi encontrado originalmente)
            filename_origem = get_filename_for_tipologia(original_tipologia)
            if not os.path.exists(filename_origem):
                messagebox.showerror("Erro", f"Arquivo de origem '{filename_origem}' não encontrado!", parent=edit_window)
                return
            df_origem = pd.read_excel(filename_origem, dtype={'Registro': str})
            for col in all_columns:
                if col not in df_origem.columns:
                    df_origem[col] = ""
            # Localiza pelo Registro original
            idx = df_origem[df_origem['Registro'].astype(str) == str(original_registro)].index
            if idx.empty:
                messagebox.showerror("Erro", f"Registro '{original_registro}' não encontrado em '{filename_origem}'.", parent=edit_window)
                return

            # Mantém o 'Registro' como está, não permitindo alteração manual
            novos_dados['Registro'] = original_registro

            # Se a tipologia não mudou, atualiza no mesmo arquivo
            if nova_tipologia == original_tipologia:
                # Atualiza todos os campos, exceto 'Registro'
                for col, val in novos_dados.items():
                    if col == 'Registro':
                        continue
                    df_origem.loc[idx, col] = val
                df_origem = df_origem[all_columns]
                if 'Registro' in df_origem.columns:
                    df_origem['Registro'] = df_origem['Registro'].astype(str)
                df_origem.to_excel(filename_origem, index=False)
            else:
                # Move o registro: remove do arquivo de origem e adiciona no destino
                registro_atualizado_dict = df_origem.loc[idx].iloc[0].to_dict()
                # Aplica novos valores editados
                for col, val in novos_dados.items():
                    if col == 'Registro':
                        continue
                    registro_atualizado_dict[col] = val
                # Remove do arquivo de origem
                df_origem = df_origem.drop(idx)
                df_origem = df_origem[all_columns]
                if 'Registro' in df_origem.columns:
                    df_origem['Registro'] = df_origem['Registro'].astype(str)
                df_origem.to_excel(filename_origem, index=False)

                # Adiciona no arquivo de destino
                filename_destino = get_filename_for_tipologia(nova_tipologia)
                if os.path.exists(filename_destino):
                    df_destino = pd.read_excel(filename_destino, dtype={'Registro': str})
                else:
                    df_destino = pd.DataFrame(columns=all_columns)
                for col in all_columns:
                    if col not in df_destino.columns:
                        df_destino[col] = ""
                # Mantém o 'Registro' original; se duplicado no destino, impede a movimentação
                if 'Registro' in df_destino.columns and not df_destino.empty:
                    if str(original_registro) in df_destino['Registro'].astype(str).tolist():
                        messagebox.showerror("Erro", f"O Registro '{original_registro}' já existe na planilha {filename_destino}! Não é possível mover mantendo a sequência.")
                        return
                # Converte o dicionário atualizado para DataFrame e concatena
                registro_df = pd.DataFrame([registro_atualizado_dict])
                # Garante todas as colunas e ordem
                for col in all_columns:
                    if col not in registro_df.columns:
                        registro_df[col] = ""
                registro_df = registro_df[all_columns]
                df_destino = pd.concat([df_destino, registro_df], ignore_index=True)
                df_destino = df_destino[all_columns]
                if 'Registro' in df_destino.columns:
                    df_destino['Registro'] = df_destino['Registro'].astype(str)
                df_destino.to_excel(filename_destino, index=False)

            messagebox.showinfo("Sucesso", "Registro atualizado com sucesso.", parent=edit_window)
            edit_window.destroy()
            atualizar_visualizacao_pesquisa()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar as alterações.\n\nErro: {e}", parent=edit_window)

    btn_salvar_edicao = ttk.Button(edit_window, text="Salvar Alterações", command=salvar_edicao)
    btn_salvar_edicao.grid(row=len(campos_registro)//2 + 3, column=0, columnspan=4, pady=20)

def ver_registro_individual():
    """Abre uma nova janela para visualizar os detalhes de um registro selecionado."""
    selected_item = result_tree.focus()
    if not selected_item:
        messagebox.showwarning("Atenção", "Selecione um registro para visualizar.")
        return

    item_values = {all_columns[i]: result_tree.item(selected_item, 'values')[i] for i in range(len(all_columns))}

    view_window = tk.Toplevel(app)
    view_window.title("Detalhes do Registro")
    view_window.geometry("500x550")
    
    main_frame = ttk.Frame(view_window, padding="15")
    main_frame.pack(expand=True, fill="both")

    row_counter = 0
    for key, value in item_values.items():
        key_label = ttk.Label(main_frame, text=f"{key}:", font=("Arial", 10, "bold"))
        key_label.grid(row=row_counter, column=0, padx=5, pady=4, sticky='ne')

        value_label = ttk.Label(main_frame, text=value, wraplength=350, justify=tk.LEFT)
        value_label.grid(row=row_counter, column=1, padx=5, pady=4, sticky='nw')
        
        row_counter += 1

    main_frame.grid_columnconfigure(1, weight=1)

    # Rodapé com botão Fechar sempre visível
    footer = ttk.Frame(view_window, padding=(15, 10))
    footer.pack(side=tk.BOTTOM, fill=tk.X)
    close_button = ttk.Button(footer, text="Fechar", command=view_window.destroy)
    close_button.pack(side=tk.RIGHT)

def ir_para_pesquisa():
    # Encontra a aba de pesquisa pelo texto para garantir que funcione após a reordenação
    for i, tab in enumerate(tab_control.tabs()):
        if tab_control.tab(tab, 'text') == 'Pesquisar Tudo':
            tab_control.select(i)
            break

def on_tab_selected(event):
    selected_tab = event.widget.select()
    if not selected_tab: return
    tab_text = event.widget.tab(selected_tab, "text")
    if tab_text == "Pesquisar Tudo":
        atualizar_visualizacao_pesquisa()

# --- DEFINIÇÕES DE LAYOUT ---
campos_registro = [
    'Data', 'Registro', 'Autor', 'Título', 'Local', 'Editora',
    'Edição', 'Volume', 'Número', 'Ano', 'Exemplar', 'Quantidade', 'Origem',
    'Cutter', 'Classificação - CDU', 'Assuntos', 'Localização'
]
tipologias = ['Livro', 'Folhetos', 'Multimeios', 'Periódicos', 'Plaquetes', 'Obras Raras', 'Folhetos de Cordel', 'Obra de Referência', 'Outros']
all_columns = campos_registro + ['Tipologia', 'Observação'] # Definido globalmente

def create_registration_form(parent_tab, tipologia):
    """Cria um formulário de cadastro completo dentro de uma aba (parent_tab)."""
    entries = []

    # 1. Frame dos campos de registro
    registro_frame = ttk.LabelFrame(parent_tab, text="Registro de Material Bibliográfico", padding="10")
    registro_frame.pack(fill=tk.X, expand=False, pady=5)

    for i, campo_text in enumerate(campos_registro):
        label = ttk.Label(registro_frame, text=f"{campo_text}:")
        label.grid(row=i // 2, column=(i % 2) * 2, padx=5, pady=5, sticky='w')
        entry = ttk.Entry(registro_frame, width=40)
        entry.grid(row=i // 2, column=(i % 2) * 2 + 1, padx=5, pady=5, sticky='ew')

        # Mascara automática para Data (DD/MM/AAAA)
        if campo_text == 'Data':
            def _on_date_keyrelease(event, widget=entry):
                txt = widget.get()
                digits = re.sub(r'\D', '', txt)[:8]
                formatted = ''
                if len(digits) >= 2:
                    formatted += digits[:2]
                    if len(digits) > 2:
                        formatted += '/' + digits[2:4]
                        if len(digits) > 4:
                            formatted += '/' + digits[4:8]
                else:
                    formatted = digits
                # Evita loop de eventos desnecessários
                if widget.get() != formatted:
                    pos = widget.index(tk.INSERT)
                    widget.delete(0, tk.END)
                    widget.insert(0, formatted)
                    try:
                        widget.icursor(min(pos + (1 if len(formatted) > len(txt) else 0), len(formatted)))
                    except Exception:
                        pass
            entry.bind('<KeyRelease>', _on_date_keyrelease)

        # Validação leve para 'Número' (permite dígitos e separador decimal)
        if campo_text == 'Número':
            def _validate_numero(action, new_value):
                # action: '1' -> inserção, '0' -> deleção
                if action == '0':
                    return True
                s = new_value.strip().replace(',', '.')
                if s == '':
                    return True
                return bool(re.match(r'^\\d*(?:\\.\\d*)?$', s))
            vcmd = (parent_tab.register(_validate_numero), '%d', '%P')
            entry.configure(validate='key', validatecommand=vcmd)

        entries.append({'label': campo_text, 'widget': entry})

    registro_frame.grid_columnconfigure(1, weight=1)
    registro_frame.grid_columnconfigure(3, weight=1)

    # 2. Frame de observação
    obs_frame = ttk.LabelFrame(parent_tab, text="Observação", padding="10")
    obs_frame.pack(fill=tk.X, expand=False, pady=5)
    obs_text = tk.Text(obs_frame, height=5)
    obs_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 3. Frame de botões
    botoes_frame = ttk.Frame(parent_tab, padding="10")
    botoes_frame.pack(fill=tk.X, pady=10)
    
    # Comandos dos botões com lambda para passar os argumentos corretos
    btn_salvar = ttk.Button(botoes_frame, text="Salvar", command=lambda: salvar_dados(tipologia, entries, obs_text))
    btn_salvar.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

    btn_limpar = ttk.Button(botoes_frame, text="Limpar Campos", command=lambda: limpar_campos(entries, obs_text))
    btn_limpar.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

    btn_pesquisar = ttk.Button(botoes_frame, text="Pesquisar Tudo", command=ir_para_pesquisa)
    btn_pesquisar.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

    btn_abrir = ttk.Button(botoes_frame, text="Ver Planilha Excel Individual", command=abrir_planilha)
    btn_abrir.pack(side=tk.RIGHT, padx=10, ipadx=10, ipady=5)

    return entries, obs_text


# --- INTERFACE GRÁFICA ---
app = tk.Tk()
app.title("Sistema Biblioteca")
app.geometry("900x700")
app.configure(bg='white') # Define um fundo branco para a janela principal

if not _license_valid():
    _request_activation(app)

# --- CABEÇALHO ---
header_frame = tk.Frame(app, bg='#ff6666')
header_frame.pack(side=tk.TOP, fill=tk.X)

# Tenta carregar e adicionar a imagem do logo
try:
    image_path = r'C:\Users\Wenderson Barboza\OneDrive\Área de Trabalho\fcja2.jpg'
    original_image = Image.open(image_path)
    # Redimensiona a imagem para uma altura de 60 pixels (um pouco maior)
    h_size = 60
    ratio = original_image.width / original_image.height
    w_size = int(h_size * ratio)
    resized_image = original_image.resize((w_size, h_size), Image.Resampling.LANCZOS)
    logo_image = ImageTk.PhotoImage(resized_image)
    # Define o ícone da janela com o mesmo logo
    try:
        app.iconphoto(True, logo_image)
    except Exception:
        pass
    
    logo_label = tk.Label(header_frame, image=logo_image, bg='#ff6666')
    logo_label.image = logo_image # Mantém uma referência
    logo_label.pack(side=tk.LEFT, padx=10, pady=2) # Padding vertical reduzido
except FileNotFoundError:
    print("AVISO: Arquivo 'fcja2.jpg' não encontrado na Área de Trabalho. O logo não será exibido.")
except Exception as e:
    print(f"AVISO: Erro ao carregar o logo: {e}")

header_label = tk.Label(header_frame, text="Sistema de Catalogação da Biblioteca", bg='#ff6666', fg='white', font=("Arial", 18, "bold"))
# O expand=True centraliza o texto no espaço restante
header_label.pack(expand=True, pady=2) # Padding vertical reduzido

# --- RODAPÉ ---
footer_frame = tk.Frame(app, bg='#ff6666', height=30)
footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
footer_label = tk.Label(footer_frame, text="Desenvolvido por Wenderson Barboza - wbs-sp@hotmail.com - 2025", bg='#ff6666', fg='white', font=("Arial", 9))
footer_label.pack(pady=5)

# --- Abas (Notebook) ---
tab_control = ttk.Notebook(app)
tab_control.pack(expand=1, fill="both", padx=10, pady=5)
tab_control.bind("<<NotebookTabChanged>>", on_tab_selected)

# Cria uma aba para cada tipologia
for tipologia in tipologias:
    tab = ttk.Frame(tab_control, padding="10")
    tab_control.add(tab, text=tipologia)
    create_registration_form(tab, tipologia)

# Adiciona a aba de Pesquisa por último
tab_pesquisa = ttk.Frame(tab_control, padding="10")
tab_control.add(tab_pesquisa, text='Pesquisar Tudo')


# --- ABA DE PESQUISA ---
search_frame = ttk.LabelFrame(tab_pesquisa, text="Filtrar Registros", padding="10")
search_frame.pack(fill=tk.X, pady=10)

search_label = ttk.Label(search_frame, text="Registro/Autor/Título:")
search_label.pack(side=tk.LEFT, padx=5)
search_entry = ttk.Entry(search_frame, width=30)
search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

search_button = ttk.Button(search_frame, text="Filtrar", command=buscar_registro)
search_button.pack(side=tk.LEFT, padx=10)

show_all_button = ttk.Button(search_frame, text="Mostrar Todos", command=atualizar_visualizacao_pesquisa)
show_all_button.pack(side=tk.LEFT, padx=10)

# Frame para os botões de ação (Editar/Excluir)
acoes_frame = ttk.Frame(tab_pesquisa, padding=(0, 10))
acoes_frame.pack(fill=tk.X)

btn_editar = ttk.Button(acoes_frame, text="Editar Selecionado", command=editar_registro)
btn_editar.pack(side=tk.LEFT, padx=5)

btn_visualizar = ttk.Button(acoes_frame, text="Registro Individual", command=ver_registro_individual)
btn_visualizar.pack(side=tk.LEFT, padx=5)

btn_excluir = ttk.Button(acoes_frame, text="Excluir Selecionado", command=excluir_registro)
btn_excluir.pack(side=tk.LEFT, padx=5)

btn_geral = ttk.Button(acoes_frame, text="Ver Planilha Geral", command=abrir_planilha_geral)
btn_geral.pack(side=tk.RIGHT, padx=5)

result_frame = ttk.Frame(tab_pesquisa)
result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

result_tree = ttk.Treeview(result_frame, columns=all_columns, show='headings')

for col in all_columns:
    result_tree.heading(col, text=col)
    # Define larguras de coluna mais apropriadas, mantendo o alinhamento central
    if col in ['Título', 'Assuntos', 'Observação']:
        result_tree.column(col, width=250, anchor='center')
    elif col in ['Autor', 'Local', 'Editora', 'Localização']:
        result_tree.column(col, width=150, anchor='center')
    else:
        result_tree.column(col, width=100, anchor='center')

vsb = ttk.Scrollbar(result_frame, orient="vertical", command=result_tree.yview)
hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=result_tree.xview)
hsb.pack(side='bottom', fill='x')
result_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

result_tree.pack(fill=tk.BOTH, expand=True)

# --- INICIALIZAÇÃO ---
inicializar_dados() # Carrega os dados na memória ao iniciar
normalizar_planilhas_existentes() # Atualiza planilhas existentes com novas colunas/ordem

# Inicia o loop da aplicação
app.mainloop()