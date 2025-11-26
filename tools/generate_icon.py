from PIL import Image
import os

SRC = 'fcja2.jpg'
DST = 'icon.ico'

if not os.path.exists(SRC):
    raise SystemExit(f"Imagem '{SRC}' não encontrada na raiz do projeto.")

im = Image.open(SRC).convert('RGBA')
# Canvas quadrado para evitar distorção
size = max(im.width, im.height)
canvas = Image.new('RGBA', (size, size), (255, 255, 255, 0))
offset = ((size - im.width) // 2, (size - im.height) // 2)
canvas.paste(im, offset)

sizes = [16, 24, 32, 48, 64, 128, 256]
canvas.save(DST, sizes=[(s, s) for s in sizes])
print(f"{DST} gerado a partir de {SRC} com tamanhos: {sizes}")
