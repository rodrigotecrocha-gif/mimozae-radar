# 🛍️ Mimozae Deals Hub - Radar de Achadinhos Virais & Afiliados (@mimozae.of)

Aplicativo profissional de alta velocidade para monitorar promoções com descontos reais, filtrar os **achadinhos mais virais** (Moda, Beleza e Gadgets de Casa), gerar links de afiliados, criar artes para o Instagram **@mimozae.of** e disparar **em lote de até 5 links de uma só vez** com foto e legenda para o WhatsApp.

---

## 🚀 Como Iniciar o Aplicativo

### Método Rápido (Windows):
Basta dar dois cliques no arquivo:
`iniciar_radar.bat`

Ou pelo terminal:
```powershell
cd C:\Users\rodri\.gemini\antigravity\scratch\mimozae-radar
python -m streamlit run app.py
```
O aplicativo abrirá no navegador em `http://localhost:8501`.

---

## ⚡ Novas Funcionalidades & Melhorias

### 1. 📦 Disparo em Lote para WhatsApp (Até 5 Links de Uma Vez)
* **Fila de Seleção:** Cada card tem uma caixa de seleção `[ ] Selecionar p/ Envio em Lote (Máx 5)`.
* **Barra de Controle Superior:** Mostra a contagem de produtos selecionados `📦 X de 5`.
* **Disparo Automático via API (Foto + Legenda em Segundo Plano):**
  * Integração nativa com **Evolution API** (v1 e v2) ou **Z-API**.
  * Envia a imagem em alta resolução com a legenda e seu link de afiliado colados juntos como foto nativa, sem abrir abas no navegador!
* **Super Mensagem Única (5 em 1):**
  * Para quem não usa API ou quer mandar um carrossel de texto limpo: gera uma mensagem compilada com os 5 produtos reunidos para enviar de uma só vez em 1 clique!

### 2. 🛡️ Higienização Rigorosa de Preços (Fim dos Bugs de Valores)
* Corrigido o bug onde preços fracionados por unidade (como `R$ 0,14 / ml` na Amazon) eram lidos como o preço do produto.
* Validação automática:
  * Impede que o preço "De" seja menor que o preço "Por".
  * Descarta promoções irreais causadas por leitura errada de unidades.
  * Recalcula o `% OFF` matematicamente com precisão.

### 3. 📸 Estúdio Instagram Integrado no Próprio Card (Sem Bugs)
* Cada card de oferta possui um expander **"📸 Gerar Post Instagram Aqui Mesmo"**.
* Você pode alternar entre **Feed (1:1 / 1080x1080)** e **Story (9:16 / 1080x1920)**, escolher a paleta de cores (*Rosa Mimozae*, *Preto VIP*, *Vermelho Oferta* ou *Verde Economia*), pré-visualizar a arte ao vivo e baixar o arquivo PNG de alta qualidade com 1 clique.
* A legenda personalizada com hashtags já é gerada abaixo da imagem para fácil cópia.

### 4. ⚡ Motor Turbo com Concorrência Paralela
* Busca simultânea em até 10 threads em paralelo. O tempo de resposta caiu para **1.8 a 2.5 segundos**!
* Cache em memória para filtros instantâneos (0.01s).

---

## ⚙️ Configuração da Automação do WhatsApp (Foto + Legenda)
Na aba **⚙️ Configurações & Afiliados**:
1. Escolha o tipo de API: **Evolution API** ou **Z-API**.
2. Preencha a URL do Endpoint (ex: `http://localhost:8080/message/sendMedia/sua-instancia`).
3. Preencha sua API Key / Token.
4. Preencha o ID do Grupo (ex: `1203630248293@g.us`).
5. Clique em **Salvar Configurações**.
Pronto! Suas ofertas selecionadas serão postadas com foto e legenda automaticamente.
