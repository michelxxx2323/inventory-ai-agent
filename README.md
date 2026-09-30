# Inventory AI Agent

Agente de estoque com IA para pequenos varejistas e e-commerces. Ele prevê a demanda de cada produto por loja e diz quanto comprar antes que o estoque acabe.

> **English summary:** AI inventory agent for small retailers. A FastAPI + Supabase backend that forecasts product demand per store with Prophet (30/60/90 days), recommends how much stock to reorder, and measures forecast accuracy against real sales.

## O problema

Em uma operação pequena de e-commerce, a reposição costuma ser feita no feeling. O resultado aparece em dois lugares: produto parado ocupando caixa, ou ruptura justamente no item que mais vende. Eu vivi isso operando minhas lojas em marketplaces e na St. Clair, e quis uma ferramenta que respondesse a uma pergunta simples: **quanto eu preciso comprar de cada produto, e quando?**

## O que o agente faz

- **Previsão de demanda por produto e por loja**, com horizonte de 30, 60 ou 90 dias, usando o modelo [Prophet](https://facebook.github.io/prophet/) sobre o histórico de vendas.
- **Recomendação de compra**: demanda prevista + 10% de margem de segurança − estoque atual. Se o resultado for positivo, o agente sugere o pedido; se não, recomenda apenas monitorar.
- **Nível de confiança** de cada previsão, calculado a partir da largura do intervalo de incerteza do modelo.
- **Validação do modelo**: antes de prever, o agente testa o modelo nos últimos 30 dias do histórico (MAE). Depois que o período passa, compara a previsão com as vendas reais e registra MAE e RMSE.
- **Gestão de estoque multi-loja**: cadastro de varejistas, lojas e produtos, ajustes de estoque com histórico de movimentações e ponto de reposição por produto.
- **Produtos mais vendidos** e trilha de auditoria de preços (preço base, preço atual e custo).

## Como funciona

```
Histórico de vendas ──► Prophet (sazonalidade diária) ──► Demanda prevista (30/60/90d)
                                                              │
Estoque atual da loja ────────────────────────────────────────┤
                                                              ▼
                                   Recomendação de compra + nível de confiança
                                                              │
                              Vendas reais do período ──► MAE / RMSE (acurácia)
```

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python, FastAPI, Pydantic |
| Banco de dados | Supabase (PostgreSQL), SQLAlchemy, Alembic |
| Previsão | Prophet, pandas, NumPy, scikit-learn |
| Testes | pytest |
| Deploy | Docker |

## Estrutura

```
├── backend/
│   ├── app/
│   │   ├── main.py        # Endpoints da API
│   │   ├── core/          # Configuração e conexão com o banco
│   │   ├── models/        # Varejistas, lojas, produtos, estoque, previsões, pedidos
│   │   ├── schemas/       # Validação de entrada e saída (Pydantic)
│   │   └── services/      # Regras de negócio, incluindo o motor de previsão
│   ├── alembic/           # Migrações do banco
│   ├── migrations/        # Scripts SQL
│   └── tests/             # Testes de produto e previsão
├── Dockerfile
└── requirements.txt
```

## Principais endpoints

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/v1/forecasts/generate` | Gera e salva a previsão de um produto em uma loja |
| `GET` | `/api/v1/stores/{store_id}/products/{product_id}/forecasts/latest` | Última previsão do produto |
| `GET` | `/api/v1/forecasts/{forecast_id}/accuracy` | Compara a previsão com as vendas reais (MAE/RMSE) |
| `GET` | `/api/v1/stores/{store_id}/inventory` | Estoque atual da loja |
| `PATCH` | `/api/v1/inventory/{inventory_id}/adjust` | Ajuste de estoque com registro no histórico |
| `GET` | `/api/v1/inventories/{inventory_id}/history` | Histórico de movimentações |
| `GET` | `/api/v1/products/top-sellers` | Produtos mais vendidos |

A documentação completa fica disponível em `/docs` com o servidor rodando.

## Como rodar

1. Clone o repositório e crie um ambiente virtual:
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```
2. Instale as dependências:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Copie `backend/.env.example` para `backend/.env` e preencha com as credenciais do seu projeto Supabase.
4. Rode as migrações e suba a API:
   ```bash
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```
5. Testes:
   ```bash
   pytest
   ```

## Status e próximos passos

- [x] Backend, modelo de dados e motor de previsão
- [x] Validação de acurácia das previsões
- [ ] Painel web: a primeira versão foi feita no Replit e não está mais disponível; vai ser refeita
- [ ] Alertas de reposição por WhatsApp
- [ ] Integração com Shopify e ERP para puxar vendas e estoque automaticamente

## Autor

**Michel Soares** · [LinkedIn](https://www.linkedin.com/in/michelsoaresafonso)
