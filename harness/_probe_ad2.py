"""Probe: agora com venture pronto (pos-1-turno), tentar r1c1 ad_campaign
e ver o fluxo passo a passo com screenshots."""
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
from world import read_cash_k

b = BizHawkBridge()
g = Game(b)

# estado ja carregado do probe anterior (mesmo processo BizHawk, estado persiste
# no emulador). Mas para robustez, salvar um savestate aqui:
b.save("../states/_venture_pronto.state")
print("savestate salvo: _venture_pronto.state")

cash0 = read_cash_k(b)
print("cash antes ad_campaign:", cash0)

g.back_to_menu()
g.open_cmd("ad_campaign")
b.advance(120)
Image.open(b.screenshot()).convert("RGB").save("../logs/action_space_map/ad2_step1.png")
print("step1 salvo")
