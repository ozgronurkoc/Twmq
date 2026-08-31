---
name: knowledge-graph
description: "Bu depo için kalıcı bilgi grafı (`.claude/bilgi_grafi.json`): modül/komut/kapı envanteri ve ölçülmüş sayı kütüğü — hangi sayı hangi komuttan çıktı, hangi belgede anılıyor, hangi bekçi tutuyor. Şunlarda kullan: bir modülün veya CLI komutunun ne yaptığı yeniden keşfedilecekse, bir belgedeki sayının kaynağı ya da bayatlığı sorulduysa, bir iddianın bekçisi var mı araştırılıyorsa, çok adımlı bir işe başlarken keşif tekrarlanmasın isteniyorsa. Tetikleyiciler: bilgi grafı, modül haritası, bu sayı nereden geliyor, hangi belgede anılıyor, hangi kapı tutuyor, keşfi önbellekle, knowledge graph."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Bilgi Grafı

## Ne işe yarar

`.claude/bilgi_grafi.json`, bu depoda **bir kez yapılan keşfin ikinci kez
yapılmaması** için tutulan yerel bir defterdir. İki şeyi kaydeder:

1. **Envanter** — hangi modül neyi yapıyor, hangi komut neyi üretiyor, hangi
   bekçi hangi iddiayı tutuyor, hangi boru hattı hangi dosyayı yazıyor.
2. **Ölçülmüş sayı kütüğü** — bir sayının **değeri**, onu **üreten komut** ve
   **anıldığı yerler** (belge + bölüm). Depodaki en pahalı bilgi budur.

İkincisi bu deponun bilinen kusurunu hedefler. `backend/tests/test_belgeler.py`
docstring'i denetimde bulunanları sayıyor: test sayısı **dört belgede dört
farklı** değerdi, `README.md` aynı hold-out isabetini bir bölümde 1 diğerinde 0
diyordu, bir API tablosunda dört uç eksikti ve iki belge daha o tabloyu kaynak
gösteriyordu. Bir sayı değiştiğinde onu anan **bütün** yerleri bulmak, her
seferinde depoyu yeniden taramayı gerektiriyor. Kütük tam bu taramayı biriktirir.

## Nerede durur ve neden git dışıdır

**Dosya**: `.claude/bilgi_grafi.json` — `.gitignore`'da, **sürümlenmez**.

Sebep bu deponun kendi kuralıdır: türetilmiş çıktı sürümlenmez, çünkü sürümlenen
türetilmiş çıktı sessizce bayatlar. Bilgi grafı tanımı gereği türetilmiştir —
tamamı depodan yeniden üretilebilir. Git'e girseydi, `git pull` yapan herkes
başkasının bir hafta önceki keşfini **bugünün gerçeği** sanarak okurdu; yani
belgelerdeki bayat sayı sorununun aynısı, üstelik bekçisiz bir kopyası olurdu.

Bunun bedeli açıktır: **graf takım arasında paylaşılmaz**, her makinede yeniden
birikir. Paylaşılan şey bu skill'in kendisidir, defterin içeriği değil.

## Yazma kuralı — kaynağı olmayan girdi yazılmaz

Bu depoda ölçülmemiş iddia yazılmaz; graf da istisna değildir. **Her girdi bir
`kaynak` alanı taşır** ve bu alan iki şeyden biridir:

* `dosya:satır` — iddianın okunduğu yer (`backend/spor_toto/health.py:1`), ya da
* çalıştırılan **komutun tam metni** ve çalıştırıldığı tarih.

`kaynak` alanı boş bir girdi yazmak yerine girdiyi **hiç yazma**. "Sanırım şu
modül şunu yapıyor" grafın işine yaramaz, zararlıdır: bir sonraki oturum onu
ölçülmüş bilgi sanır.

Ayrıca her girdi, dayandığı dosyanın **içerik hash'ini** taşır. Bayatlığı
görünür kılan mekanizma budur (aşağıya bak).

## İşlemler

### 1. Oku

```bash
test -f .claude/bilgi_grafi.json && python3 -m json.tool .claude/bilgi_grafi.json | head -40
```

Dosya yoksa bu bir hata değildir: graf henüz birikmemiştir. Boş iskeletle başlat
(şema: [references/schema.md](references/schema.md)).

### 2. Sorgula

Doğrudan `jq`/`python3` ile. Hazır tarifler:
[references/sorgular.md](references/sorgular.md).

```bash
# "0,579 nereden geliyor, nerelerde anılıyor?"
python3 -c "
import json;g=json.load(open('.claude/bilgi_grafi.json'))
for s in g['sayilar']:
    if '0,579' in s['deger']: print(s['ne'],'|',s['ureten'],'|',s['anildigi_yerler'])
"
```

### 3. Güncelle

Keşif **yapıldıktan sonra**, aynı oturumda yaz — sonraya bırakılan kayıt
yazılmaz. Birleştirme kuralı: aynı `yol`/`deger` varsa üzerine yaz, yeni
`anildigi_yerler` girdilerini **ekle** (üzerine yazma, birleştir).

### 4. Tazelik denetle

Graf bayatlığını **kendisi** göstermeli, kullanıcı fark etmemeli:

```bash
python3 - <<'PY'
import json, subprocess, pathlib
g = json.load(open('.claude/bilgi_grafi.json'))
bayat = []
for bolum in ('moduller', 'kapilar', 'boru_hatlari'):
    for gd in g.get(bolum, []):
        p = pathlib.Path(gd['yol'])
        if not p.exists():
            bayat.append((bolum, gd['yol'], 'DOSYA YOK')); continue
        h = subprocess.run(['git','hash-object',gd['yol']],
                           capture_output=True, text=True).stdout.strip()
        if h != gd.get('hash'):
            bayat.append((bolum, gd['yol'], 'DEGISTI'))
print(f"HEAD kaydı: {g['git']['head']}  ·  şimdi: "
      + subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip())
print(f"bayat girdi: {len(bayat)}")
for b in bayat: print('  ', *b)
PY
```

Bayat girdiyle ne yapılır: **silinir ya da yeniden ölçülür, düzeltilmiş sayılmaz.**
Kaynak dosya değişmişse o girdinin taşıdığı iddia artık ölçülmemiş bir iddiadır.

Sayı kütüğü için ek denetim: kayıtlı `anildigi_yerler` hâlâ o sayıyı içeriyor mu?

```bash
grep -n "0,579" README.md docs/*.md backend/README.md || echo "artik hicbir belgede yok"
```

### 5. Envanterin mekanik kısmını üret

Modül/komut/test listesi elle yazılmaz, ölçülür:

```bash
ls backend/spor_toto/*.py backend/scripts/*.py            # modüller, boru hatları
grep -rc 'def test_' backend/tests/*.py | awk -F: '{s+=$2} END {print s}'   # test sayısı
python -m spor_toto.health --list                          # kapı/kontrol envanteri
bash scripts/check.sh                                      # kalite kapısı (CI de bunu çağırır)
```

Modül **görevi** için o dosyanın docstring'i okunur ve `kaynak` olarak
`yol:1` yazılır — özet uydurulmaz, docstring'den alınır.

## Bu depoda gerçek kullanım

**Sayı değişti, nereleri düzeltmem gerek?**
Kütükte `deger` ara → `anildigi_yerler` listesini al → hepsini düzelt →
`bash scripts/check.sh` ile bekçilere sor. Kütükte yoksa: depoyu tara, düzelt,
**sonra kütüğe yaz** ki üçüncü kez taranmasın.

**Bu iddianın bekçisi var mı?**
`kapilar` bölümünde `tuttugu_iddia` alanlarında ara. Yoksa cevap "bekçisi yok" —
ve bu, bekçi yazmak için bir gerekçedir, grafa not düşmek için değil.

**Yeni bir katmana dokunacağım, neyi bilmem lazım?**
`moduller` + `boru_hatlari` bölümlerini oku: hangi script hangi dosyayı üretiyor,
hangisi git dışı, yeniden üretme komutu ne. Bu bilgi `.gitignore` yorumlarında
zaten yazıyor — graf onu tek yerde toplar, **yerine geçmez**.

## Sınırlar

* **Graf kanıt değildir.** Çelişki halinde kazanan sırayla: çalışan ölçüm > kod >
  belge > graf. Graf en zayıf halkadır çünkü en kolay bayatlar.
* **Kaynak kodu değiştirmez.** Yalnızca `.claude/bilgi_grafi.json` yazar.
* **Kod üretmez.** Keşfi önbelleğe alır, uygulama yazmaz.
* **Veri taşımaz.** Oran arşivi, korpus, StatsBomb özetleri, gizli anahtar —
  hiçbiri grafa girmez; graf yalnızca *nerede olduklarını* ve *nasıl üretildiklerini*
  kaydeder. (StatsBomb verisi lisans gereği depoda dağıtılamaz; bkz. `.gitignore`.)
* **Bekçisi yoktur.** Bu grafın doğruluğunu tutan bir pytest kapısı **yok** —
  tazelik denetimi elle çağrılır. Bu yüzden git dışıdır: bekçisiz bir iddia
  sürümlenmez.

## Referanslar

* [references/schema.md](references/schema.md) — JSON şeması, alan alan
* [references/sorgular.md](references/sorgular.md) — sorgu ve güncelleme tarifleri
* [references/sinirlar.md](references/sinirlar.md) — bayatlık, boyut, gizlilik
* [ORIGIN.md](ORIGIN.md) — nereden geldi, ne kadarı yeniden yazıldı
