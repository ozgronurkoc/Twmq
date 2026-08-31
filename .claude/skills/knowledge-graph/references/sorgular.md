# Sorgu ve güncelleme tarifleri

Hepsi depo kökünden çalışır. `jq` varsayılmaz; depo Python olduğu için
`python3` kullanılır.

## Boş grafı başlat

```bash
python3 - <<'PY'
import json, subprocess, datetime, pathlib
head = subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
dal  = subprocess.run(['git','rev-parse','--abbrev-ref','HEAD'],capture_output=True,text=True).stdout.strip()
g = {"surum":1,
     "yazildi":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
     "git":{"head":head,"dal":dal},
     "moduller":[], "komutlar":[], "kapilar":[], "sayilar":[], "boru_hatlari":[]}
pathlib.Path('.claude').mkdir(exist_ok=True)
json.dump(g, open('.claude/bilgi_grafi.json','w'), ensure_ascii=False, indent=2)
print("başlatıldı")
PY
```

## Modül envanterini docstring'lerden üret

Görev metni **uydurulmaz**, dosyanın kendi docstring'inin ilk satırından alınır.

```bash
python3 - <<'PY'
import ast, json, subprocess, glob, datetime
g = json.load(open('.claude/bilgi_grafi.json'))
var = {m['yol'] for m in g['moduller']}
for yol in sorted(glob.glob('backend/spor_toto/*.py')):
    if yol.endswith('__init__.py') or yol in var: continue
    d = ast.get_docstring(ast.parse(open(yol,encoding='utf-8').read()))
    if not d: continue                      # docstring yok -> girdi de yok
    h = subprocess.run(['git','hash-object',yol],capture_output=True,text=True).stdout.strip()
    g['moduller'].append({"yol":yol,"gorev":d.strip().splitlines()[0],
                          "kaynak":f"{yol}:1","hash":h})
g['yazildi']=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
json.dump(g, open('.claude/bilgi_grafi.json','w'), ensure_ascii=False, indent=2)
print(f"{len(g['moduller'])} modül")
PY
```

`backend/scripts/*.py` için aynısı `boru_hatlari`'na yazılır; `uretir` ve
`git_disi` alanları `.gitignore` yorumlarından okunur, tahmin edilmez.

## Modül ara

```bash
python3 -c "
import json,sys;g=json.load(open('.claude/bilgi_grafi.json'))
a=sys.argv[1].lower()
for m in g['moduller']:
    if a in m['yol'].lower() or a in m['gorev'].lower(): print(m['yol'],'—',m['gorev'])
" kalibr
```

## Sayı kütüğüne kayıt ekle

Bir sayıyı düzeltirken **aynı oturumda** yaz; yoksa dördüncü kez taranır.

```bash
python3 - <<'PY'
import json, datetime
g = json.load(open('.claude/bilgi_grafi.json'))
yeni = {"deger":"0,579", "ne":"Piyasanın Brier skoru.",
        "ureten":"<sayıyı üreten tam komut>", "olculdu":"2026-08-31",
        "anildigi_yerler":["README.md:§1.1"]}
for s in g['sayilar']:
    if s['deger']==yeni['deger'] and s['ne']==yeni['ne']:
        # anıldığı yerler BIRLESTIRILIR, üzerine yazılmaz
        s['anildigi_yerler']=sorted(set(s['anildigi_yerler'])|set(yeni['anildigi_yerler']))
        s.update({k:v for k,v in yeni.items() if k!='anildigi_yerler'}); break
else:
    g['sayilar'].append(yeni)
g['yazildi']=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
json.dump(g, open('.claude/bilgi_grafi.json','w'), ensure_ascii=False, indent=2)
PY
```

## Bir sayının anıldığı yerleri doğrula

Kütük iddia eder, `grep` karar verir:

```bash
S="0,579"
python3 -c "
import json,sys;g=json.load(open('.claude/bilgi_grafi.json'))
print('\n'.join(y for s in g['sayilar'] if s['deger']==sys.argv[1] for y in s['anildigi_yerler']))
" "$S"
grep -rn "$S" README.md backend/README.md docs/*.md | cut -d: -f1,2
```

İki liste ayrışıyorsa **grep kazanır**: kütük düzeltilir.

## Kapı envanterini üret

```bash
grep -rn '^def test_' backend/tests/test_belgeler.py | head -20   # belge bekçileri
python -m spor_toto.health --list                                  # sağlık kontrolleri
```

`tuttugu_iddia` alanı test fonksiyonunun docstring'inin ilk satırıdır — testin
adından türetilmez.

## Bayat girdileri temizle

Tazelik denetimi (`SKILL.md` §4) bayat listesi verir. Temizleme kuralı:
**yeniden ölç ya da sil.** Bayat girdiyi "muhtemelen hâlâ doğru" diye bırakmak,
grafı bekçisiz bir belgeye dönüştürür — bu deponun kaçındığı şeyin tam kendisi.

```bash
python3 - <<'PY'
import json, subprocess, pathlib, datetime
g = json.load(open('.claude/bilgi_grafi.json'))
for bolum in ('moduller','kapilar','boru_hatlari'):
    kalan=[]
    for gd in g.get(bolum,[]):
        p=pathlib.Path(gd['yol'])
        h=subprocess.run(['git','hash-object',gd['yol']],capture_output=True,text=True).stdout.strip() if p.exists() else None
        if h==gd.get('hash'): kalan.append(gd)
        else: print("silindi:",bolum,gd['yol'])
    g[bolum]=kalan
g['yazildi']=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
json.dump(g, open('.claude/bilgi_grafi.json','w'), ensure_ascii=False, indent=2)
PY
```

## Grafı tamamen at

Yeniden üretilebilir olduğu için en ucuz onarım budur:

```bash
rm -f .claude/bilgi_grafi.json
```
