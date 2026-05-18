from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm 
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Q
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import CadastroForm, AvaliacaoForm, UserUpdateForm, PerfilUpdateForm, ProdutoForm
from .models import *
from .carrinho import Carrinho
from django.contrib.admin.views.decorators import staff_member_required

import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import io
import base64

def exportar_grafico_para_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    imagem_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    return imagem_base64

def home_view(request):
    produtos = Produto.objects.all()
    avaliacoes_top = Avaliacao.objects.filter(nota=5)
    
    context = {
        'nome_empresa': 'TechStore',
        'produtos': produtos,
        'avaliacoes': avaliacoes_top
    }
    return render(request, 'home.html', context)

@login_required
def produtos_view(request):
    form_produto = ProdutoForm()
    form_avaliacao = AvaliacaoForm()

    if request.method == 'POST':
        if 'submit_produto' in request.POST:
            form_produto = ProdutoForm(request.POST, request.FILES)
            if form_produto.is_valid():
                novo_produto = form_produto.save(commit=False)
                
                loja_do_usuario = Loja.objects.filter(equipe=request.user).first()
                if not loja_do_usuario:
                    loja_do_usuario = Loja.objects.create(
                        nome_da_loja=f"Loja de {request.user.username}",
                        descricao="Criada automaticamente pelo sistema ao adicionar o primeiro produto."
                    )
                    loja_do_usuario.equipe.add(request.user)
                
                novo_produto.loja = loja_do_usuario
                novo_produto.save()
                messages.success(request, "Produto adicionado com sucesso!")
                return redirect('produtos')
            else:
                messages.error(request, "Erro ao adicionar produto. Verifique os dados.")

        elif 'submit_avaliacao' in request.POST:
            form_avaliacao = AvaliacaoForm(request.POST)
            if form_avaliacao.is_valid():
                avaliacao = form_avaliacao.save(commit=False)
                avaliacao.usuario = request.user
                
                try:
                    avaliacao.save()
                    messages.success(request, "Avaliação enviada com sucesso!")
                except IntegrityError:
                    messages.error(request, "Você já avaliou este produto anteriormente.")
                
                return redirect('produtos')
            else:
                messages.error(request, "Erro ao enviar avaliação. Verifique os campos.")

    produtos = Produto.objects.all()

    q = request.GET.get('q', '').strip()
    if q:
        produtos = produtos.filter(nome__icontains=q)

    categoria_selecionada = request.GET.get('categoria', '').strip()
    if categoria_selecionada:
        produtos = produtos.filter(categoria=categoria_selecionada)

    preco_min = request.GET.get('preco_min')
    if preco_min:
        try:
            produtos = produtos.filter(preco__gte=float(preco_min))
        except ValueError:
            pass

    preco_max = request.GET.get('preco_max')
    if preco_max:
        try:
            produtos = produtos.filter(preco__lte=float(preco_max))
        except ValueError:
            pass

    categorias_choices = getattr(Produto, 'CATEGORIA_CHOICES', [])
    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = list(Favorito.objects.filter(usuario=request.user).values_list('produto_id', flat=True))
    
    context = {
        'usuario': request.user.username,
        'produtos': produtos,
        'favoritos_ids': favoritos_ids,
        'categorias_choices': categorias_choices,
        'categoria_selecionada': categoria_selecionada,
        'form_produto': form_produto,
        'form_avaliacao': form_avaliacao,
        'q': q,
        'favoritos_ids': favoritos_ids,
    }
    return render(request, 'produtos.html', context)

def detalhe_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id) 
    
    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = list(Favorito.objects.filter(usuario=request.user).values_list('produto_id', flat=True))
    
    context = {
        'produto': produto,
        'favoritos_ids': favoritos_ids,
    }
    return render(request, 'detalhe_produto.html', context)

@login_required
def meus_pedidos(request):
    pedidos_usuario = Pedido.objects.filter(comprador=request.user).prefetch_related('itens__produto').order_by('-data_pedido')
    
    context = {
        'pedidos': pedidos_usuario
    }
    
    return render(request, 'meus_pedidos.html', context)

@login_required
def detalhes_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, comprador=request.user)
    
    context = {
        'pedido': pedido
    }
    return render(request, 'detalhes_pedido.html', context)

@login_required
def favoritar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    favorito = Favorito.objects.filter(usuario=request.user, produto=produto)

    if favorito.exists():
        favorito.delete()
    else:
        Favorito.objects.create(usuario=request.user, produto=produto)

    return redirect('produtos')

@login_required
def lista_favoritos(request):
    favoritos = Favorito.objects.filter(usuario=request.user).select_related('produto')
    return render(request, 'favoritos.html', {'favoritos': favoritos})

@login_required
def alternar_favorito(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    favorito_existente = Favorito.objects.filter(usuario=request.user, produto=produto)

    if favorito_existente.exists():
        favorito_existente.delete()
        favoritado = False
    else:
        Favorito.objects.create(usuario=request.user, produto=produto)
        favoritado = True

    return JsonResponse({'status': 'success', 'favoritado': favoritado})

@login_required
@require_POST
def toggle_favorito(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    favorito, created = Favorito.objects.get_or_create(usuario=request.user, produto=produto)
    
    if not created:
        favorito.delete()
        return JsonResponse({'status': 'removido'})
    
    return JsonResponse({'status': 'adicionado'})

def detalhe_carrinho(request):
    carrinho = Carrinho(request)
    return render(request, 'carrinho.html', {'carrinho': carrinho})

def carrinho_adicionar(request, produto_id):
    carrinho = Carrinho(request)
    produto = get_object_or_404(Produto, id=produto_id)
    
    quantidade = 1
    override = False
    
    if request.method == 'POST':
        quantidade = int(request.POST.get('quantidade', 1))
        override = request.POST.get('override', 'False') == 'True'
        
    quantidade_no_carrinho = 0
    for item in carrinho:
        item_produto = item.get('produto') if isinstance(item, dict) else getattr(item, 'produto', None)
        if item_produto and item_produto.id == produto.id:
            quantidade_no_carrinho = item.get('quantidade', 0) if isinstance(item, dict) else getattr(item, 'quantidade', 0)
            break

    quantidade_final = quantidade if override else (quantidade_no_carrinho + quantidade)

    if quantidade_final > produto.estoque:
        messages.error(
            request, 
            f'Não é possível adicionar mais unidades de "{produto.nome}". '
            f'Você já tem {quantidade_no_carrinho} un. no carrinho e o estoque máximo é de {produto.estoque} un.'
        )
        return redirect(request.META.get('HTTP_REFERER', 'produtos'))
        
    carrinho.adicionar(produto=produto, quantidade=quantidade, override_quantidade=override)
    
    if override:
        messages.warning(request, f'"{produto.nome}" foi removido do seu carrinho!')
    else:
        messages.success(request, f'"{produto.nome}" foi adicionado ao seu carrinho!')
    
    return redirect(request.META.get('HTTP_REFERER', 'produtos'))

def carrinho_remover(request, produto_id):
    carrinho = Carrinho(request)
    produto = get_object_or_404(Produto, id=produto_id)
    carrinho.remover(produto)
    messages.warning(request, f'"{produto.nome}" foi removido do seu carrinho!')
    return redirect('detalhe_carrinho')

@login_required
def finalizar_compra(request):
    carrinho = Carrinho(request)

    if len(carrinho) == 0:
        messages.info(request, 'Seu carrinho está vazio. Adicione produtos antes de finalizar.')
        return redirect('detalhe_carrinho')

    try:
        perfil = request.user.perfil
    except Exception:
        perfil = None

    if request.method == 'POST':
        pedido = Pedido.objects.create(
            comprador=request.user,
            total=carrinho.get_total_preco(),
            status='pendente'
        )

        for item in carrinho:
            produto = item['produto']
            quantidade_comprada = item['quantidade']

            if produto.estoque < quantidade_comprada:
                messages.error(request, f'Desculpe, o produto "{produto.nome}" só possui {produto.estoque} unidades disponíveis.')
                pedido.delete()
                return redirect('detalhe_carrinho')

            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                preco=item['preco'],
                quantidade=quantidade_comprada
            )

            produto.estoque -= quantidade_comprada
            produto.save()


        carrinho.limpar()  
        messages.success(request, f'Pedido #{pedido.id} realizado com sucesso!')
        return redirect('produtos')  

    context = {
        'carrinho': carrinho,
        'perfil': perfil
    }
    return render(request, 'finalizar_compra.html', context)

@login_required(login_url='login')
def dashboard_view(request):
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = PerfilUpdateForm(request.POST, request.FILES, instance=perfil)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            perfil_instance = p_form.save(commit=False)
            
            num = p_form.cleaned_data.get('numero')
            rua = p_form.cleaned_data.get('endereco')
            
            if num and rua:
                perfil_instance.endereco = f"{rua} - Nº {num}"
            elif rua:
                perfil_instance.endereco = rua
                
            perfil_instance.save()
            messages.success(request, 'Seu perfil foi atualizado com sucesso!')
            return redirect('dashboard')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = PerfilUpdateForm(instance=perfil)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'perfil': perfil
    }
    return render(request, 'dashboard.html', context)

@login_required
def avaliar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.usuario = request.user
            avaliacao.produto = produto
            avaliacao.save()
            return redirect('detalhe_produto', produto_id=produto.id)
    return redirect('detalhe_produto', produto_id=produto.id)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Seja bem-vindo, {user.username}! Login realizado com sucesso.")
            return redirect('home')
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'login.html', {'form': form})

def cadastro_view(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            tipo_perfil = form.cleaned_data.get('tipo_pessoa')
            nome_loja_digitado = form.cleaned_data.get('nome_da_loja')
            
            if tipo_perfil == 'PJ' and nome_loja_digitado:
                nova_loja = Loja.objects.create(
                    nome_da_loja=nome_loja_digitado,
                    descricao=f"Loja de {user.username}"
                )
                nova_loja.equipe.add(user)
            
            messages.success(request, f"Conta criada com sucesso para {user.username}! Faça o seu login.")
            return redirect('login')
        else:
            print("ERROS DE VALIDAÇÃO DO CADASTRO:", form.errors)
            for campo, erros in form.errors.items():
                for erro in erros:
                    messages.error(request, f"Erro no campo {campo}: {erro}")
    else:
        form = CadastroForm()
        
    return render(request, 'cadastro.html', {'form': form})
    
def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu com sucesso.")
    return redirect('login')

@login_required
def alterar_senha(request):
    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')

        if not nova_senha or not confirmar_senha:
            messages.error(request, 'Por favor, preencha todos os campos.')
            return redirect('alterar_senha')

        if nova_senha != confirmar_senha:
            messages.error(request, 'As senhas não coincidem. Tente novamente.')
            return redirect('alterar_senha')

        if len(nova_senha) < 8:
            messages.error(request, 'A nova senha deve conter pelo menos 8 caracteres.')
            return redirect('alterar_senha')

        user = request.user
        user.set_password(nova_senha)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, 'Sua senha foi alterada com sucesso!')
        return redirect('dashboard')

    return render(request, 'alterar_senha.html')

def atendimento_view(request):
    perfil = getattr(request.user, 'perfil', None) 
    return render(request, 'atendimento.html', {'perfil': perfil})

@staff_member_required
def dashboard_bi_view(request):
    lojas = Loja.objects.all()
    produtos = Produto.objects.all()
    
    nomes_lojas = []
    valores_lucro_loja = []
    for loja in lojas:
        lucro_loja = sum(float(p.calcular_margem_abs()) * p.estoque for p in loja.produtos.all())
        nomes_lojas.append(loja.nome_da_loja)
        valores_lucro_loja.append(lucro_loja)

    categorias_lucro = {}
    for p in produtos:
        cat = p.categoria if hasattr(p, 'categoria') and p.categoria else "Geral"
        lucro_total_produto = float(p.calcular_margem_abs()) * p.estoque
        categorias_lucro[cat] = categorias_lucro.get(cat, 0) + lucro_total_produto

    # --- GERANDO GRÁFICO DE BARRAS (Isolando a figura) ---
    fig_barras = plt.figure(figsize=(10, 5))
    plt.style.use('dark_background')
    plt.bar(nomes_lojas, valores_lucro_loja, color='#58a6ff') 
    plt.title('LUCRO POR REGIONAL', color='#58a6ff')
    grafico_barras = exportar_grafico_para_base64(fig_barras)
    plt.close(fig_barras)

    # --- GERANDO GRÁFICO DE PIZZA (Isolando a figura) ---
    fig_pizza = plt.figure(figsize=(7, 7))
    plt.style.use('dark_background')
    plt.pie(categorias_lucro.values(), labels=categorias_lucro.keys(), autopct='%1.1f%%', colors=['#58a6ff', '#51cf66', '#ff7b72'])
    plt.title('MIX DE LUCRO POR CATEGORIA', color='#51cf66')
    grafico_pizza = exportar_grafico_para_base64(fig_pizza)
    plt.close(fig_pizza)

    produtos_ranking = sorted(produtos, key=lambda p: float(p.calcular_margem_abs()), reverse=True)[:5]

    context = {
        'grafico': grafico_barras,
        'grafico_pizza': grafico_pizza,
        'total_geral': sum(valores_lucro_loja),
        'total_lojas': lojas.count(),
        'produtos_lucrativos': produtos_ranking,
    }
    return render(request, 'admin/dashboard_bi.html', context)

@staff_member_required
def dashboard_logistica_view(request):
    produtos = Produto.objects.all()
    capital_total = sum(float(p.preco_custo) * p.estoque for p in produtos)
    estoque_critico = [p for p in produtos if p.estoque < 5]
    
    qtd_critico = len([p for p in produtos if p.estoque < 5])
    qtd_atencao = len([p for p in produtos if 5 <= p.estoque <= 10])
    qtd_saudavel = len([p for p in produtos if p.estoque > 10])

    # --- GERANDO GRÁFICO DE LOGÍSTICA (Isolando a figura) ---
    fig_log = plt.figure(figsize=(8, 5))
    plt.style.use('dark_background')
    
    categorias = ['Crítico (<5)', 'Atenção (5-10)', 'Saudável (>10)']
    contagem = [qtd_critico, qtd_atencao, qtd_saudavel]
    cores = ['#ff7b72', '#f1e05a', '#51cf66']

    plt.bar(categorias, contagem, color=cores)
    plt.title('SAÚDE DO INVENTÁRIO (QUANTIDADE)', color='#58a6ff', pad=20)
    
    grafico_estoque = exportar_grafico_para_base64(fig_log)
    plt.close(fig_log)

    context = {
        'estoque_critico': estoque_critico,
        'capital_total': capital_total,
        'grafico_estoque': grafico_estoque,
        'total_pecas': sum(p.estoque for p in produtos)
    }
    return render(request, 'admin/dashboard_logistica.html', context)