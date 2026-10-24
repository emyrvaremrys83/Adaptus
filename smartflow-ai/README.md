# SmartFlow AI — üretim planlama MVP

Hackathon demosu için kural tabanlı, makine yeteneklerini gözeten bir üretim planlama paneli. Örnek işler ve makineler simüle edilmiştir; gerçek fabrika, sensör veya ERP bağlantısı yoktur. Ayrı AI tahmin bölümü, sentetik verilerle eğitilen yerel bir regresyon modeli kullanır.

## Özellikler

- 3 makine ve 12 örnek Job (JOB-1001–JOB-1012)
- English/Türkçe dil seçimi (demo varsayılanı English)
- Sabit açık görünüm; uygulama içinde tema seçicisi yok
- Operasyon yetenekleri, işlem ve hazırlık süreleri, öncelik, teslim hedefi ve malzeme hazır zamanı
- Aynı Job'lar üzerinde başlangıç ve öncelik odaklı sezgisel plan karşılaştırması
- Makine bazında hazırlık ve işlem segmentlerini ayıran Gantt çizelgesi
- Her planın kendi bitiş ufkuna göre kullanım oranı ve boşta kalma; toplam işlem ve son bitiş KPI'ları
- Job ekleme, düzenleme, silme ve yerel `jobs.json` dosyasında saklama
- Atama ve sıra farklarına dayanan açıklamalar
- AI süreleriyle yeniden planlama anahtarı; bitiş farkı ve teslim gecikmelerinin karşılaştırılması

## Kurulum ve başlatma

Python 3.10 veya üzeri gerekir. ZIP'i açın ve `smartflow-ai` klasöründe terminal açın.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

## Planlama yaklaşımı

`planner.py` arayüzden bağımsızdır. Başlangıç planı Job'ları giriş sırasıyla ele alır. Öncelik planı yüksek öncelik, erken teslim, malzeme hazır zamanı ve eklenme sırasını kullanır; her Job sadece yetenekli makinelere atanır. Job, malzeme hazır olmadan başlamaz. Hazırlık ve işlem aynı makineyi ayrı fakat ardışık aralıklarla kullanır. KPI karşılaştırması her planı kendi bitiş ufkunda ölçer. Algoritma sezgiseldir; teslim gecikmesi veya evrensel optimum garantisi yoktur.


## AI işlem süresi tahmini

`AI Tahmini / AI Estimates` sekmesinde operasyon, işlem süresi ve hazırlık süresini değiştirerek yerel regresyon modelini deneyebilirsiniz. Kayıtlı işler için girilen süre ve AI tahmini yan yana gösterilir. Sayfanın üstündeki **AI süreleriyle planla / Plan with AI durations** anahtarı tahminleri Gantt planına ve KPI'lara uygular. Anahtarı kapatınca girilen sürelerle oluşturulan plana dönülür. `jobs.json` ve düzenleme formundaki orijinal süreler bu anahtar tarafından değiştirilmez.

- ZIP'i açtıktan sonra proje klasöründe `.venv\Scripts\python.exe -m pip install -r requirements.txt` çalıştırın.
- Ardından `.venv\Scripts\python.exe -m streamlit run app.py` ile başlatın.
- İlk AI açılışında model yerel olarak eğitilir ve bellekte önbelleğe alınır.
- Kurulumdan sonra API anahtarı, internet veya GPU gerekmez.
- 2.400 sentetik kaydın 1.800'ü eğitim, 600'ü ayrı test için kullanılır.
- Ekrandaki ortalama mutlak hata yalnızca simülasyon testine aittir; gerçek fabrika doğruluğu değildir.
- Desteklenen girişler: işlem süresi 0,5–48 saat, hazırlık 0–12 saat, uygulamadaki beş operasyon.
- Gerçek kullanım için geçmiş planlanan/gerçekleşen işlem süreleriyle yeniden eğitim ve doğrulama gerekir.

Hızlı deneme: Sol paneldeki **1 · Kısa**, **2 · Orta**, **3 · Uzun** butonlarıyla demo değiştirin. Her sette aynı 12 işin farklı işlem ve hazırlık süreleri bulunur. Demo seçimi mevcut iş listesinin yerine geçer ve `jobs.json` dosyasına kaydedilir. AI anahtarı kapalıyken toplam işlem süreleri sırasıyla 22, 44 ve 88 saattir. AI Tahmini sekmesi de aynı seçili işlerin tahminlerini gösterir; burada ayrı demo seçimi yoktur. Elle giriş ve model test sonuçları, **Ayrıntılar ve elle deneme** bölümündedir.

## AI ile planlama denemesi

1. Sol panelden **2 · Orta / 2 · Medium** demosunu seçin.
2. **Plan karşılaştırması / Plan comparison** sekmesini açık tutun.
3. Sayfanın üstündeki **AI süreleriyle planla / Plan with AI durations** anahtarını açın.
4. Gantt çubukları ve üstteki KPI'lar tahmini işlem süreleriyle güncellenir. Zaman ekseni, görsel karşılaştırma için iki modda da ortak tutulur.
5. **AI süreleri planı nasıl değiştiriyor?** bölümünde girilen sürelerle ve AI süreleriyle hesaplanan bitiş tarihlerini, saat farkını ve geciken iş sayılarını inceleyin.
6. **AI Tahmini** sekmesindeki **AI etki haritasında** tüm işleri, yalnızca yeni gecikenleri veya AI planındaki tüm gecikenleri filtreleyin. Çubuklar her işin bitiş kaymasını gösterir. Alttan bir iş seçerek girilen plan bitişini, AI plan bitişini, teslim hedefini ve gecikme süresini yan yana inceleyin. Bu grafik, anahtar kapalıyken de iki süre senaryosunu karşılaştırır.
7. Grafiklerin altındaki teslim tablosunda kırmızı satırlar geciken, turuncu satırlar yalnızca AI süreleriyle geciken işlerdir. **Yalnızca aktif planda geciken işleri göster** seçeneğini kapatarak zamanında işleri de görebilirsiniz.
8. Anahtarı kapatın; orijinal sürelerle hesaplanan plan geri gelir. Aynı denemeyi Short ve Long üzerinde tekrarlayın.

İki Gantt grafiği başlangıç sırası ile öncelik sırasını karşılaştırır ve ikisi de seçili süre kaynağını kullanır. Yeni AI etki bölümü ise aynı öncelik kuralı, işler ve başlangıç zamanı altında orijinal sürelerle AI sürelerini karşılaştırır. Böylece sıralama etkisi ile süre tahmininin etkisi birbirine karışmaz.

Gecikme, işin planlanan bitişinin teslim hedefini aştığı süredir; tam teslim saatinde biten iş zamanındadır. Hesapta kuyrukta bekleme, hazırlık, makine yeteneği, sabit makine atamaları ve malzeme hazır zamanı dikkate alınır. Teslim tablosu öncelik planına aittir. Bunlar simülasyon modelinin plan tahminleridir; gerçek gecikme olasılığı veya teslim garantisi değildir.

Model NumPy ile en küçük kareler yöntemiyle eğitilir. Operasyon, süre ve hazırlık girdilerinden bir süre çarpanı öğrenir; katsayılar eğitim verilerinden hesaplanır. Simülasyondaki operasyon yavaşlamaları ve rastgele sapmalar gerçek üretim bulguları değildir.

Teslimde `.venv`, `__pycache__` ve günlük dosyalarını dahil etmeyin. `timeline_navigation` ve `.streamlit` klasörlerini kaynak dosyalarıyla birlikte tutun.
ZIP içinde sanal ortam bulunmaz; alıcı önce yukarıdaki kurulum komutlarını çalıştırmalıdır. Testleri de aynı `.venv` Python'uyla çalıştırın; bilgisayardaki genel Python ortamı farklı paketlere sahip olabilir.
