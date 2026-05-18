from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
    path('produtos/', views.produtos_view, name='produtos'),
    path('minha-conta/', views.dashboard_view, name='dashboard'),
    path('meus-pedidos/', views.meus_pedidos, name='meus_pedidos'),
    path('detalhes-pedido/<int:pedido_id>/', views.detalhes_pedido, name='detalhes_pedido'),
    path('atendimento/', views.atendimento_view, name='atendimento'),
    path('produto/<int:produto_id>/',views.detalhe_produto,name='detalhe_produto'),
    path('produto/<int:id>/', views.detalhe_produto, name='detalhe_produto'),
    path('carrinho/', views.detalhe_carrinho, name='detalhe_carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.carrinho_adicionar, name='carrinho_adicionar'),
    path('carrinho/remover/<int:produto_id>/', views.carrinho_remover, name='carrinho_remover'),
    path('carrinho/finalizar/', views.finalizar_compra, name='finalizar_compra'),
    path('favoritos/', views.lista_favoritos, name='favoritos'),
    path('favoritos/alternar/<int:produto_id>/', views.alternar_favorito, name='alternar_favorito'),
    path('favoritar/<int:produto_id>/',views.favoritar_produto,name='favoritar_produto'),
    path('favorito/toggle/<int:produto_id>/', views.toggle_favorito, name='toggle_favorito'),
    # Rota do Business Intelligence - Acesso Restrito
    path('dashboard-bi/', views.dashboard_bi_view, name='dashboard_bi'),
    path('bi/logistica/', views.dashboard_logistica_view, name='dashboard_logistica'),
]
