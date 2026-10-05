from engine.tez import sinav


def r(**kw):
    base = dict(kural="IZLE", AL="-", AL_TF="-", AL_vade="-", SAT="-", SAT_TF="-",
                cakisma="hayir", cizgi_kirik=False)
    base.update(kw)
    return base


def test_cikacak_weekly_uzun_tutuyor():
    s, _ = sinav(r(kural="TREND_HAFTALIK", AL="AL", AL_TF="weekly", AL_vade="uzun"), "çıkacak", "weekly")
    assert s == "tutuyor"


def test_cikacak_kisa_al_kismen():
    s, n = sinav(r(kural="1H_EMA_YIGIN", AL="AL", AL_TF="1H/4H", AL_vade="kisa"), "çıkacak", "daily")
    assert s == "kısmen" and any("kısa" in x for x in n)


def test_cikacak_cakisma_tutmuyor():
    s, _ = sinav(r(AL="AL", AL_vade="orta", SAT="SAT", SAT_TF="daily", cakisma="evet"), "çıkacak", "daily")
    assert s == "tutmuyor"


def test_cikacak_hacimsiz():
    s, _ = sinav(r(kural="TREND_HAFTALIK", AL="YOK"), "çıkacak", "weekly")
    assert s == "tutmuyor"


def test_donecek_tepki():
    s, _ = sinav(r(kural="TEPKI_ZONE", AL="AL", AL_TF="daily", AL_vade="kisa"), "dönecek", "daily")
    assert s == "tutuyor"


def test_donecek_kirik():
    s, _ = sinav(r(kural="IZLE", cizgi_kirik="True"), "dönecek", "daily")
    assert s == "tutmuyor"


def test_kirilacak():
    assert sinav(r(SAT="SAT", SAT_TF="daily"), "kırılacak / düşecek", "daily")[0] == "tutuyor"
    assert sinav(r(SAT="SAT", SAT_TF="weekly"), "kırılacak / düşecek", "daily")[0] == "kısmen"
    assert sinav(r(AL="AL"), "kırılacak / düşecek", "daily")[0] == "tutmuyor"
