# Twmq — ajan notu

## Keşfe başlamadan önce bilgi grafına bak

`.claude/bilgi_grafi.json` bu depoda **bir kez yapılmış keşfin defteridir**:
modül görevleri, kalite kapıları, boru hatları ve **ölçülmüş sayı kütüğü**
(hangi sayı hangi komuttan çıktı, hangi belgede anılıyor). Git dışıdır ve
tamamı depodan yeniden üretilebilir.

**Kural:** aşağıdaki sorulardan biriyle karşılaşınca depoyu taramadan **önce**
grafı sorgula. Cevap graftaysa tarama yapma; yoksa tara, sonra grafa yaz.

* bir modül / komut / boru hattı ne yapıyor
* bir sayı nereden geliyor, hangi belgede anılıyor, bayat mı
* bir iddianın bekçisi var mı

```bash
python3 .claude/graf_sorgu.py ozet          # bölüm bölüm girdi sayısı
python3 .claude/graf_sorgu.py modul kalibr  # modül ara (terimsiz = hepsi)
python3 .claude/graf_sorgu.py komut check    # komut envanterinde ara
python3 .claude/graf_sorgu.py sayi 1901     # sayı kütüğünde ara
python3 .claude/graf_sorgu.py kapi belge    # bekçi ara
python3 .claude/graf_sorgu.py tazelik       # bayat girdi var mı
```

**Grafın tamamını okuma** (~8.000 token); yalnızca ilgili bölümü sorgula.

**Graf kanıt değildir.** Çelişkide sıra: çalışan ölçüm > kod > belge > graf.
`tazelik` bayat girdi gösteriyorsa o girdi **yeniden ölçülür**, düzeltilmiş
sayılmaz. Ayrıntı: `.claude/skills/knowledge-graph/SKILL.md`.
