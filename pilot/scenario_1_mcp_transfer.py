"""
Szenario 1: Einfache dCHF-Transaktion via MCP
1. AI-Agent schlägt Überweisung vor
2. Gravit prüft (Epistemic Core)
3. Mensch signiert
4. FINMA-Beweis wird generiert
"""

def run():
    # 1. MCP-Vorschlag simulieren
    proposal = {
        "from": "client_wallet_a",
        "to": "client_wallet_b", 
        "amount": 1000,
        "asset": "dCHF",
        "reason": "Investment in tokenized equity"
    }
    
    # 2. Gravit Verifikation
    verifier = EpistemicVerifier()
    result = verifier.verify(proposal)
    
    # 3. FINMA-Log
    logger.log(result, compliance=True)
    
    # 4. Ausgabe
    assert result.valid == True
    print("✅ Szenario 1 erfolgreich")