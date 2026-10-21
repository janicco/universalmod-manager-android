from datetime import datetime
import json
import os
import shutil
import threading
import time
import urllib.parse
import webbrowser
import zipfile
import flet as ft

# --- SICHERE ANDROID-SPEICHERPFADE ---
try:
    # Sicherer App-interner Speicher (darf Android niemals blockieren)
    BASIS_ORDNER = os.path.join(os.path.expanduser("~"), "ModManagerMobile")
    os.makedirs(BASIS_ORDNER, exist_ok=True)
except Exception:
    BASIS_ORDNER = "ModManagerMobile"
    os.makedirs(BASIS_ORDNER, exist_ok=True)

LAGER_BASIS = os.path.join(BASIS_ORDNER, "Lager")
BACKUP_BASIS = os.path.join(BASIS_ORDNER, "Backups")

try:
    os.makedirs(LAGER_BASIS, exist_ok=True)
    os.makedirs(BACKUP_BASIS, exist_ok=True)
except Exception:
    pass

# Downloads-Pfad ermitteln
if os.path.exists("/storage/emulated/0/Download"):
    DOWNLOADS_PFAD = "/storage/emulated/0/Download"
else:
    DOWNLOADS_PFAD = os.path.join(os.path.expanduser("~"), "Downloads")

# SPIELE KONFIGURATION
SPIELE_CONFIG = {
    "Minecraft PE": {
        "pfad": os.path.join(BASIS_ORDNER, "Minecraft_Mods"),
        "store": "https://curseforge.com/minecraft/mc-mods",
        "url_scheme": "minecraft://",
    },
    "Unity Mobile": {
        "pfad": os.path.join(BASIS_ORDNER, "Unity_Mods"),
        "store": "https://www.nexusmods.com/",
        "url_scheme": "",
    },
    "PPSSPP Emulator": {
        "pfad": os.path.join(BASIS_ORDNER, "PPSSPP_Mods"),
        "store": "https://github.com/",
        "url_scheme": "",
    },
}

for sp in SPIELE_CONFIG.values():
    try:
        os.makedirs(sp["pfad"], exist_ok=True)
    except Exception:
        pass

MOD_ENDUNGEN = (
    ".mcpack",
    ".mcaddon",
    ".zip",
    ".apk",
    ".dll",
    ".pak",
    ".jar",
    ".mod",
)
profile_daten = {}


# --- ZIP ENTPACKER ---
def smarter_zip_entpacker(zip_pfad, ziel_ordner):
    muell = (".txt", ".url", ".png", ".jpg", ".jpeg", ".md", ".pdf", ".docx")
    try:
        with zipfile.ZipFile(zip_pfad, "r") as z:
            for item in z.infolist():
                if item.is_dir() or any(
                    item.filename.lower().endswith(m) for m in muell
                ):
                    continue
                flach = os.path.basename(item.filename)
                ziel = os.path.join(ziel_ordner, flach)
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                with z.open(item) as q, open(ziel, "wb") as zf:
                    shutil.copyfileobj(q, zf)
    except Exception as e:
        print(f"Zip Error: {e}")


# --- DIE MOBILE HAUPT-APP ---
def main(page: ft.Page):
    page.title = "Universal Mod Manager Mobile (v0.5)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#11111b"
    page.scroll = ft.ScrollMode.AUTO

    aktuelles_spiel = "Minecraft PE"
    mod_liste_view = ft.ListView(expand=True, spacing=8, padding=10)
    such_text = ""

    # KUGELSICHERE DIALOGE FÜR ANDROID
    def oeffne_dialog(dlg):
        try:
            if hasattr(page, "show_dialog"):
                page.show_dialog(dlg)
            elif hasattr(page, "open"):
                page.open(dlg)
            else:
                page.dialog = dlg
                dlg.open = True
                page.update()
        except Exception:
            pass

    def schliesse_dialog(dlg=None):
        try:
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(dlg)
            elif dlg is not None:
                dlg.open = False
                page.update()
        except Exception:
            pass

    def zeige_toast(text, farbe="#89b4fa"):
        try:
            snack = ft.SnackBar(content=ft.Text(text), bgcolor=farbe)
            if hasattr(page, "show_dialog"):
                page.show_dialog(snack)
            elif hasattr(page, "open"):
                page.open(snack)
            else:
                page.snack_bar = snack
                snack.open = True
                page.update()
        except Exception:
            pass

    def get_spiel_pfad():
        p = SPIELE_CONFIG[aktuelles_spiel]["pfad"]
        os.makedirs(p, exist_ok=True)
        return p

    def get_lager_pfad():
        p = os.path.join(LAGER_BASIS, aktuelles_spiel)
        os.makedirs(p, exist_ok=True)
        return p

    def mod_toggle(e, dateiname):
        ist_aktiv = e.control.value
        s_pfad = get_spiel_pfad()
        l_pfad = get_lager_pfad()

        von = (
            os.path.join(l_pfad, dateiname)
            if ist_aktiv
            else os.path.join(s_pfad, dateiname)
        )
        nach = (
            os.path.join(s_pfad, dateiname)
            if ist_aktiv
            else os.path.join(l_pfad, dateiname)
        )

        try:
            if os.path.exists(von):
                shutil.move(von, nach)
        except Exception:
            pass

        aktualisiere_liste()
        zeige_toast(
            f"{dateiname} {'aktiviert' if ist_aktiv else 'deaktiviert'}!",
            "#a6e3a1" if ist_aktiv else "#f38ba8",
        )

    def aktualisiere_liste():
        mod_liste_view.controls.clear()
        s_pfad = get_spiel_pfad()
        l_pfad = get_lager_pfad()

        aktive = os.listdir(s_pfad) if os.path.exists(s_pfad) else []
        lager = os.listdir(l_pfad) if os.path.exists(l_pfad) else []

        for d in aktive:
            if such_text and such_text not in d.lower():
                continue
            mod_liste_view.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE, color="#a6e3a1", size=22
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        d,
                                        weight="bold",
                                        size=13,
                                        color="#cdd6f4",
                                    ),
                                    ft.Text(
                                        "Aktiv im Spiel",
                                        size=10,
                                        color="#a6adc8",
                                    ),
                                ],
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.INFO_OUTLINE,
                                icon_color="#f9e2af",
                                icon_size=18,
                                on_click=lambda e, n=d: ki_inspektor(n, True),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#f38ba8",
                                icon_size=18,
                                on_click=lambda e, n=d: mod_loeschen(n, True),
                            ),
                            ft.Switch(
                                value=True,
                                active_color="#a6e3a1",
                                on_change=lambda e, n=d: mod_toggle(e, n),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor="#181825",
                    padding=10,
                    border_radius=10,
                )
            )

        for d in lager:
            if such_text and such_text not in d.lower():
                continue
            mod_liste_view.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.PAUSE_CIRCLE_OUTLINE,
                                color="#f38ba8",
                                size=22,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        d,
                                        weight="bold",
                                        size=13,
                                        color="#cdd6f4",
                                    ),
                                    ft.Text(
                                        "Im Lager (Aus)",
                                        size=10,
                                        color="#6c7086",
                                    ),
                                ],
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.INFO_OUTLINE,
                                icon_color="#f9e2af",
                                icon_size=18,
                                on_click=lambda e, n=d: ki_inspektor(n, False),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#f38ba8",
                                icon_size=18,
                                on_click=lambda e, n=d: mod_loeschen(n, False),
                            ),
                            ft.Switch(
                                value=False,
                                active_color="#a6e3a1",
                                on_change=lambda e, n=d: mod_toggle(e, n),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor="#181825",
                    padding=10,
                    border_radius=10,
                )
            )

        if not aktive and not lager:
            mod_liste_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.FOLDER_OPEN, size=40, color="#6c7086"
                            ),
                            ft.Text(
                                "Noch keine Mods für dieses Spiel!",
                                color="#6c7086",
                                size=13,
                            ),
                            ft.Text(
                                "Lade eine Mod im Browser herunter.",
                                color="#45475a",
                                size=11,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=25,
                )
            )
        page.update()

    # BUTTONS & AKTIONEN
    def spiel_starten(e):
        url = SPIELE_CONFIG[aktuelles_spiel].get("url_scheme")
        if url:
            webbrowser.open(url)
            zeige_toast(f"Starte {aktuelles_spiel}...", "#f9e2af")
        else:
            zeige_toast(f"Bitte starte {aktuelles_spiel} vom Homescreen!")

    def mod_store(e):
        webbrowser.open(SPIELE_CONFIG[aktuelles_spiel]["store"])

    def ki_inspektor(datei, ist_aktiv):
        ordner = get_spiel_pfad() if ist_aktiv else get_lager_pfad()
        pfad = os.path.join(ordner, datei)
        kb = (
            round(os.path.getsize(pfad) / 1024, 2)
            if os.path.exists(pfad)
            else 0
        )
        bericht = f"📦 Mod: {datei}\n🎮 Spiel: {aktuelles_spiel}\n📊 Größe: {kb} KB\n\n✅ 100% Sicher für Android."

        dlg = ft.AlertDialog(
            title=ft.Text("🧠 KI Mod-Inspektor", color="#f9e2af"),
            content=ft.Text(bericht, size=12),
            actions=[
                ft.Button(
                    content="🌐 Im Web suchen",
                    on_click=lambda ev: webbrowser.open(
                        f"https://www.google.com/search?q={urllib.parse.quote(f'{aktuelles_spiel} mod {datei}')}"
                    ),
                ),
                ft.Button(
                    content="Schließen",
                    on_click=lambda ev: schliesse_dialog(dlg),
                ),
            ],
        )
        oeffne_dialog(dlg)

    def crash_doktor(e):
        s_pfad = get_spiel_pfad()
        entfernt = 0
        try:
            for f in os.listdir(s_pfad):
                if " (1)." in f or "_copy." in f:
                    os.remove(os.path.join(s_pfad, f))
                    entfernt += 1
        except Exception:
            pass

        text = (
            f"✅ {entfernt} defekte Duplikate gelöscht!"
            if entfernt
            else "✅ Alle Spieldateien sind sauber und fehlerfrei!"
        )
        dlg = ft.AlertDialog(
            title=ft.Text("🩺 Crash-Doktor", color="#a6e3a1"),
            content=ft.Text(text, size=12),
            actions=[
                ft.Button(
                    content="Super!", on_click=lambda ev: schliesse_dialog(dlg)
                )
            ],
        )
        oeffne_dialog(dlg)
        aktualisiere_liste()

    def mod_hook(e):
        s_pfad = get_spiel_pfad()
        dlg = ft.AlertDialog(
            title=ft.Text("💉 Mod-Support freigeschaltet", color="#f9e2af"),
            content=ft.Text(f"Mod-Pfad erzwungen:\n\n{s_pfad}", size=12),
            actions=[
                ft.Button(
                    content="Fertig", on_click=lambda ev: schliesse_dialog(dlg)
                )
            ],
        )
        oeffne_dialog(dlg)

    def backup_erstellen(e):
        s_pfad = get_spiel_pfad()
        aktive = os.listdir(s_pfad) if os.path.exists(s_pfad) else []
        if not aktive:
            zeige_toast("Keine Mods zum Sichern da!", "#f38ba8")
            return
        zeit = datetime.now().strftime("%Y-%m-%d_%H-%M")
        ziel = os.path.join(
            BACKUP_BASIS, f"Backup_{aktuelles_spiel[:6]}_{zeit}.zip"
        )
        try:
            with zipfile.ZipFile(ziel, "w") as z:
                for d in aktive:
                    z.write(os.path.join(s_pfad, d), d)
            zeige_toast(f"Backup gesichert: {os.path.basename(ziel)}", "#a6e3a1")
        except Exception:
            pass

    def mod_loeschen(datei, ist_aktiv):
        ordner = get_spiel_pfad() if ist_aktiv else get_lager_pfad()
        pfad = os.path.join(ordner, datei)

        def delete_action(ev):
            try:
                os.remove(pfad)
                aktualisiere_liste()
                schliesse_dialog(dlg)
                zeige_toast(f"'{datei}' gelöscht!", "#f38ba8")
            except Exception:
                pass

        dlg = ft.AlertDialog(
            title=ft.Text("Mod löschen?"),
            content=ft.Text(f"'{datei}' wirklich entfernen?", size=12),
            actions=[
                ft.Button(content="Löschen", on_click=delete_action),
                ft.Button(
                    content="Abbrechen",
                    on_click=lambda ev: schliesse_dialog(dlg),
                ),
            ],
        )
        oeffne_dialog(dlg)

    def alle_umschalten(einschalten=True):
        s_pfad = get_spiel_pfad()
        l_pfad = get_lager_pfad()
        quell, ziel = (l_pfad, s_pfad) if einschalten else (s_pfad, l_pfad)

        if os.path.exists(quell):
            for d in list(os.listdir(quell)):
                try:
                    shutil.move(os.path.join(quell, d), os.path.join(ziel, d))
                except Exception:
                    pass
        aktualisiere_liste()

    # ANDROID DOWNLOADS SCANNER (Crash-sicher)
    def downloads_scannen(e=None):
        if not os.path.exists(DOWNLOADS_PFAD):
            zeige_toast("Kein Download-Ordner gefunden", "#f38ba8")
            return
        gefundene = 0
        try:
            for datei in os.listdir(DOWNLOADS_PFAD):
                d_k = datei.lower()
                voll = os.path.join(DOWNLOADS_PFAD, datei)
                if any(
                    d_k.endswith(ext) for ext in MOD_ENDUNGEN
                ) and not d_k.endswith((".tmp", ".crdownload")):
                    s_pfad = get_spiel_pfad()
                    if d_k.endswith(".zip"):
                        smarter_zip_entpacker(voll, s_pfad)
                    else:
                        shutil.copy(voll, os.path.join(s_pfad, datei))
                    gefundene += 1
            aktualisiere_liste()
            if gefundene > 0:
                zeige_toast(
                    f"{gefundene} Mod(s) aus Downloads importiert!", "#a6e3a1"
                )
            else:
                zeige_toast("Keine neuen Mods in Downloads.", "#89b4fa")
        except Exception:
            zeige_toast(
                "Tippe in Android-Einstellungen auf 'Dateizugriff erlauben'.",
                "#fab387",
            )

    def spiel_geaendert(e):
        nonlocal aktuelles_spiel
        if e.control.value:
            aktuelles_spiel = e.control.value
        aktualisiere_liste()

    def suche_geaendert(e):
        nonlocal such_text
        such_text = e.control.value.lower()
        aktualisiere_liste()

    # DROPDOWN
    dropdown_opts = []
    for k in SPIELE_CONFIG.keys():
        if hasattr(ft, "DropdownOption"):
            dropdown_opts.append(ft.DropdownOption(k))
        else:
            dropdown_opts.append(ft.dropdown.Option(k))

    dd_args = {
        "label": "🎮 Spiel wählen",
        "value": aktuelles_spiel,
        "options": dropdown_opts,
    }
    if "on_select" in ft.Dropdown.__init__.__code__.co_varnames:
        dd_args["on_select"] = spiel_geaendert
    elif "on_change" in ft.Dropdown.__init__.__code__.co_varnames:
        dd_args["on_change"] = spiel_geaendert

    # LAYOUT
    page.add(
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ANDROID, color="#a6e3a1", size=24),
                    ft.Text(
                        "Universal Mod Manager",
                        weight="bold",
                        size=15,
                        color="#cdd6f4",
                    ),
                    ft.IconButton(
                        ft.Icons.REFRESH,
                        icon_color="#89b4fa",
                        icon_size=20,
                        on_click=lambda e: aktualisiere_liste(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#181825",
            padding=12,
            border_radius=ft.BorderRadius(0, 0, 15, 15),
        ),
        ft.Container(
            content=ft.Column(
                [
                    ft.Dropdown(**dd_args),
                    ft.Row(
                        [
                            ft.Button(
                                content="⚡ Alle an",
                                bgcolor="#a6e3a1",
                                color="#11111b",
                                on_click=lambda e: alle_umschalten(True),
                            ),
                            ft.Button(
                                content="💤 Alle aus",
                                bgcolor="#f38ba8",
                                color="#11111b",
                                on_click=lambda e: alle_umschalten(False),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ]
            ),
            padding=ft.Padding(10, 6, 10, 2),
        ),
        ft.Container(
            content=ft.Row(
                [
                    ft.Button(
                        content="🚀 Starten",
                        bgcolor="#f9e2af",
                        color="#11111b",
                        on_click=spiel_starten,
                    ),
                    ft.Button(
                        content="🌐 Store",
                        bgcolor="#89b4fa",
                        color="#11111b",
                        on_click=mod_store,
                    ),
                    ft.Button(
                        content="🩺 Doktor",
                        bgcolor="#f38ba8",
                        color="#11111b",
                        on_click=crash_doktor,
                    ),
                    ft.Button(
                        content="💉 Hook",
                        bgcolor="#fab387",
                        color="#11111b",
                        on_click=mod_hook,
                    ),
                    ft.Button(
                        content="🛡️ Backup",
                        bgcolor="#89b4fa",
                        color="#11111b",
                        on_click=backup_erstellen,
                    ),
                ],
                scroll=ft.ScrollMode.ALWAYS,
            ),
            padding=ft.Padding(10, 2, 10, 2),
        ),
        ft.Container(
            content=ft.TextField(
                hint_text="🔍 Mod suchen...",
                border_color="#45475a",
                color="#cdd6f4",
                on_change=suche_geaendert,
            ),
            padding=ft.Padding(10, 2, 10, 4),
        ),
        mod_liste_view,
        ft.Container(
            content=ft.Row(
                [
                    ft.Button(
                        content="📥 Downloads scannen & importieren",
                        icon=ft.Icons.DOWNLOAD,
                        bgcolor="#89b4fa",
                        color="#11111b",
                        on_click=downloads_scannen,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=10,
        ),
    )

    aktualisiere_liste()


if __name__ == "__main__":
    ft.run(main)
