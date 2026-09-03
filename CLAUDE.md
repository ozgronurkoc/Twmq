# Twmq — ajan notu

## Keşfe başlamadan önce bilgi grafına bak

`.claude/bilgi_grafi.json` bu depoda **bir kez yapılmış keşfin defteridir**:
modül görevleri, kalite kapıları, boru hatları ve **ölçülmüş sayı kütüğü**
(hangi sayı hangi komuttan çıktı, hangi belgede anılıyor). Git dışıdır ve
tamamı depodan yeniden üretilebilir.

Mesajın grafla ilgiliyse **ilgili girdiler bu mesaja zaten enjekte edilmiştir**
(`.claude/hooks/user-prompt.sh`). Yukarıda "Bilgi grafından ... ilgili girdiler"
başlıklı bir blok görüyorsan o blok ölçülmüş kayıttır — aynı şeyi yeniden
tarama. Blok "tek mesaja sığmaz" diyorsa sorguyu **sen** çalıştır.

**Kural:** aşağıdaki sorulardan biriyle karşılaşınca depoyu taramadan **önce**
grafı sorgula. Cevap graftaysa tarama yapma; yoksa tara, sonra grafa yaz.

* bir modül / komut / boru hattı ne yapıyor
* bir sayı nereden geliyor, hangi belgede anılıyor, bayat mı
* bir iddianın bekçisi var mı

```bash
python3 .claude/graf_sorgu.py ozet          # bölüm bölüm girdi sayısı
python3 .claude/graf_sorgu.py modul kalibr  # modül ara (terimsiz = hepsi)
python3 .claude/graf_sorgu.py komut check    # komut envanterinde ara
python3 .claude/graf_sorgu.py sayi 1931     # sayı kütüğünde ara
python3 .claude/graf_sorgu.py kapi belge    # bekçi ara
python3 .claude/graf_sorgu.py tazelik       # bayat girdi var mı
```

**Grafın tamamını okuma** (~8.000 token); yalnızca ilgili bölümü sorgula.

Envanter bölümleri (`moduller`/`kapilar`/`boru_hatlari`) **oturum başında
kendiliğinden tazelenir** (`.claude/hooks/session-start.sh`, ~0,3 sn), o yüzden
onlara güvenebilirsin. `sayilar` tazelenmez, yalnızca **denetlenir**: oturum
açılışında "SUPHELI SAYI" uyarısı gördüysen o sayı **yeniden ölçülmeden
kullanılmaz**.

`sayilar` ve `komutlar` elle birikir ama **artık git'e girer**:
`.claude/olcum_kutugu.json` sürümlenir, envanter (`.claude/bilgi_grafi.json`)
sürümlenmez. Ayrım şu: envanter *türetilmiştir* (depodan 0,3 sn'de yeniden
üretilir), ölçüm kütüğü *bir koşum kaydıdır* (komut koşmayı gerektirir,
taranarak üretilemez). Önceden ikisi de git dışıydı ve kütük her taze klonda
— yani her uzak oturumda — sıfırdan başlıyordu.

Kütük boş gelirse bu artık "klon taze" değil **"hiç ölçülmemiş"** demektir.
O durumda kural seni taramadan muaf tutmaz: **ölç, sonra kütüğe yaz.**

**Graf kanıt değildir.** Çelişkide sıra: çalışan ölçüm > kod > belge > graf.
`tazelik` bayat girdi gösteriyorsa o girdi **yeniden ölçülür**, düzeltilmiş
sayılmaz. Ayrıntı: `.claude/skills/knowledge-graph/SKILL.md`.
