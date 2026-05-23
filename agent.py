import sys
import json
import os
import yfinance as yf
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Alle likvide aksjer på Oslo Børs ─────────────────────────────────────────
OSLO_BORS = [
    "EQNR.OL","DNB.OL","MOWI.OL","TEL.OL","ORK.OL","AKRBP.OL","YAR.OL",
    "SALM.OL","SUBC.OL","KOG.OL","NHY.OL","RECSI.OL","STB.OL","GJF.OL",
    "SCHA.OL","AKER.OL","BAKKA.OL","LSG.OL","PGS.OL","FRO.OL","NOD.OL",
    "SRBNK.OL","TOM.OL","AGAS.OL","GOGL.OL","WSTL.OL","BWLPG.OL","SATS.OL",
    "VEI.OL","BDRILL.OL","NEXT.OL","ARCUS.OL","AFG.OL","ATEA.OL","ADE.OL",
    "AUSS.OL","BELCO.OL","BONHR.OL","BORR.OL","BWE.OL","BWO.OL",
    "CIRCA.OL","CRAYON.OL","DNSB.OL","DOF.OL","DOFG.OL","EIOF.OL",
    "ENTRA.OL","EPR.OL","FLNG.OL","FORTE.OL","GRIEG.OL","HEXAGON.OL",
    "HBC.OL","HECO.OL","HUNT.OL","IDEX.OL","IHR.OL","IOX.OL","JSHIP.OL",
    "KID.OL","MING.OL","MHG.OL","MPCC.OL","MPC.OL","NAPA.OL","NEL.OL",
    "NRC.OL","NRS.OL","NSKOG.OL","ODF.OL","PARB.OL","PEXIP.OL","PHO.OL",
    "REC.OL","SAGA.OL","SCATC.OL","SDRL.OL","SEER.OL","SNI.OL","SOFF.OL",
    "SPOL.OL","SWF.OL","SYNNOVE.OL","TGS.OL","VAR.OL","VISTIN.OL",
    "VOW.OL","WWI.OL","XXL.OL","ZAL.OL","NYKD.OL","PLCS.OL","STRONG.OL",
    "SLEM.OL","MNTR.OL","PDRILL.OL","HRGI.OL","AUTOSTK.OL","AKER.OL",
    "AKSO.OL","AMSC.OL","ARCH.OL","AYFIE.OL","BOUVET.OL","CLOUD.OL",
    "CONTX.OL","DFDS.OL","ELK.OL","ENDUR.OL","FJORD.OL","FKRAFT.OL",
    "FLEX.OL","FPAR.OL","GIGA.OL","GRO.OL","HAFNI.OL","HAVI.OL",
    "INIFY.OL","JINF.OL","KAHOT.OL","KOMPLETT.OL","LINK.OL","MEDI.OL",
    "NAUR.OL","NORAM.OL","NORD.OL","NORBIT.OL","NORSE.OL","NRSF.OL",
    "NUMND.OL","OCEAN.OL","OET.OL","OKEA.OL","OTEC.OL","PCIB.OL",
    "PROT.OL","PSI.OL","QUAN.OL","RAKP.OL","REACH.OL","ROCC.OL",
    "SATG.OL","SEABIRD.OL","SELF.OL","SGSOL.OL","SIKRI.OL","SLONG.OL",
    "SMOP.OL","SOAG.OL","SOLON.OL","SPNO.OL","SPORT.OL","STRAX.OL",
    "SVEG.OL","TIDE.OL","TOTG.OL","TSCO.OL","ULTI.OL","VARMT.OL",
    "VISB.OL","WILCO.OL","XPLRA.OL",
]
# Fjern duplikater
OSLO_BORS = list(dict.fromkeys(OSLO_BORS))

SNAPSHOT_0915 = "snapshot_0915.json"
SNAPSHOT_1200 = "snapshot_1200.json"
TOPP10_FIL    = "topp10_fall.json"


# ── Hent kurser for alle aksjer ───────────────────────────────────────────────
def hent_alle_kurser():
    print(f"Henter kurser for {len(OSLO_BORS)} aksjer...")
    kurser = {}
    # Hent i bolker på 50 for å unngå timeout
    bolk = 50
    for i in range(0, len(OSLO_BORS), bolk):
        gruppe = OSLO_BORS[i:i+bolk]
        try:
            tickers = yf.Tickers(" ".join(gruppe))
            for ticker in gruppe:
                try:
                    pris = tickers.tickers[ticker].fast_info["last_price"]
                    if pris and float(pris) > 0:
                        kurser[ticker] = round(float(pris), 2)
                except Exception:
                    pass
        except Exception as e:
            print(f"  Feil i bolk {i}: {e}")
    print(f"  Hentet {len(kurser)} kurser")
    return kurser


# ── E-postsending ─────────────────────────────────────────────────────────────
def send_html_epost(subject, html):
    avsender = os.environ["EPOST_AVSENDER"]
    passord  = os.environ["EPOST_PASSORD"]
    mottaker = [m.strip() for m in os.environ["EPOST_MOTTAKER"].split(",")]
    melding  = MIMEMultipart("alternative")
    melding["Subject"] = subject
    melding["From"]    = avsender
    melding["To"]      = ", ".join(mottaker)
    melding.attach(MIMEText(html, "html"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(avsender, passord)
        server.sendmail(avsender, mottaker, melding.as_string())
    print("E-post sendt!")


# ── HTML-hjelp ────────────────────────────────────────────────────────────────
def pst_celle(verdi):
    if verdi is None:
        return "–"
    farge = "#1a7f37" if verdi >= 0 else "#cf222e"
    pil   = "▲" if verdi >= 0 else "▼"
    return f'<span style="color:{farge};font-weight:bold">{pil} {verdi:+.2f}%</span>'


def bygg_tabell(rader, kolonner):
    header = "".join(
        f'<th style="background:#1a1a2e;color:white;padding:10px 14px;'
        f'text-align:{"left" if i==0 else "right"};white-space:nowrap">{k}</th>'
        for i, k in enumerate(kolonner)
    )
    tbody = ""
    for i, rad in enumerate(rader):
        bg = "#f5f7fa" if i % 2 == 0 else "#ffffff"
        tbody += f'<tr style="background:{bg}">' + "".join(
            f'<td style="padding:9px 14px;text-align:{"left" if j==0 else "right"};'
            f'border-bottom:1px solid #e8e8e8">{celle}</td>'
            for j, celle in enumerate(rad)
        ) + "</tr>"
    return (
        f'<table border="0" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;font-size:14px;width:100%">'
        f'<thead><tr>{header}</tr></thead>'
        f'<tbody>{tbody}</tbody></table>'
    )


def html_wrapper(tittel, dato, ingress, tabell):
    return f"""
    <html><body style="font-family:Arial,sans-serif;padding:24px;
                        max-width:900px;margin:auto;color:#333">
      <h2 style="color:#1a1a2e;border-bottom:3px solid #cf222e;
                  padding-bottom:10px">{tittel}</h2>
      <p style="color:#555;margin-bottom:20px">{dato} &nbsp;·&nbsp; {ingress}</p>
      {tabell}
      <p style="color:#bbb;font-size:11px;margin-top:24px">
        Sendt automatisk av Oslo Børs-agenten
      </p>
    </body></html>"""


# ── JOBB 09:15 ────────────────────────────────────────────────────────────────
def jobb_0915():
    kurser = hent_alle_kurser()
    with open(SNAPSHOT_0915, "w") as f:
        json.dump({"tidspunkt": datetime.now().isoformat(), "kurser": kurser}, f)
    print(f"Snapshot 09:15 lagret – {len(kurser)} aksjer")


# ── JOBB 12:00 ────────────────────────────────────────────────────────────────
def jobb_1200():
    with open(SNAPSHOT_0915) as f:
        snap_0915 = json.load(f)["kurser"]

    kurser_1200 = hent_alle_kurser()
    with open(SNAPSHOT_1200, "w") as f:
        json.dump({"tidspunkt": datetime.now().isoformat(), "kurser": kurser_1200}, f)

    # Beregn fall
    endringer = []
    for ticker, p0 in snap_0915.items():
        p1 = kurser_1200.get(ticker)
        if p0 and p1 and p0 > 0:
            pst = round((p1 - p0) / p0 * 100, 2)
            endringer.append({
                "ticker":          ticker,
                "navn":            ticker.replace(".OL", ""),
                "p0915":           p0,
                "p1200":           p1,
                "pst_0915_1200":   pst,
            })

    endringer.sort(key=lambda x: x["pst_0915_1200"])
    topp10 = endringer[:10]

    with open(TOPP10_FIL, "w") as f:
        json.dump(topp10, f)

    dato = datetime.now().strftime("%Y-%m-%d")
    rader = []
    for r in topp10:
        rader.append([
            f'<b>{r["navn"]}</b><br><small style="color:#888">{r["ticker"]}</small>',
            f'{r["p0915"]:.2f}',
            f'{r["p1200"]:.2f}',
            pst_celle(r["pst_0915_1200"]),
        ])

    tabell = bygg_tabell(
        rader,
        ["Selskap", "Kurs 09:15", "Kurs 12:00", "Endring"]
    )
    html = html_wrapper(
        "📉 Topp 10 kursfall – kl 12:00",
        dato,
        "De 10 aksjene med størst prosentvis fall fra åpning",
        tabell
    )
    send_html_epost(f"📉 Topp 10 kursfall 12:00 – {dato}", html)


# ── JOBB 15:30 ────────────────────────────────────────────────────────────────
def jobb_1530():
    with open(SNAPSHOT_0915) as f:
        snap_0915 = json.load(f)["kurser"]
    with open(SNAPSHOT_1200) as f:
        snap_1200 = json.load(f)["kurser"]
    with open(TOPP10_FIL) as f:
        topp10 = json.load(f)

    # Hent kun de 10 utvalgte
    kurser_1530 = {}
    for r in topp10:
        try:
            pris = yf.Ticker(r["ticker"]).fast_info["last_price"]
            kurser_1530[r["ticker"]] = round(float(pris), 2)
        except Exception:
            kurser_1530[r["ticker"]] = None

    dato = datetime.now().strftime("%Y-%m-%d")
    rader = []
    for r in topp10:
        ticker = r["ticker"]
        p0 = r["p0915"]
        p1 = r["p1200"]
        p2 = kurser_1530.get(ticker)
        pst_em = round((p2 - p1) / p1 * 100, 2) if p1 and p2 else None

        rader.append([
            f'<b>{r["navn"]}</b><br><small style="color:#888">{ticker}</small>',
            f"{p0:.2f}",
            f"{p1:.2f}",
            f"{p2:.2f}" if p2 else "–",
            pst_celle(r["pst_0915_1200"]),
            pst_celle(pst_em),
        ])

    tabell = bygg_tabell(
        rader,
        ["Selskap", "Kurs 09:15", "Kurs 12:00", "Kurs 15:30",
         "09:15 → 12:00", "12:00 → 15:30"]
    )
    html = html_wrapper(
        "📊 Oppfølging – kl 15:30",
        dato,
        "Utvikling for dagens 10 største kursfall",
        tabell
    )
    send_html_epost(f"📊 Kursoppfølging 15:30 – {dato}", html)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Bruk: python agent.py [0915|1200|1530]")
        sys.exit(1)

    jobb = sys.argv[1]
    print(f"Oslo Børs-agent – jobb: {jobb} ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

    if   jobb == "0915": jobb_0915()
    elif jobb == "1200": jobb_1200()
    elif jobb == "1530": jobb_1530()
    else:
        print(f"Ukjent jobb: {jobb}")
        sys.exit(1)
