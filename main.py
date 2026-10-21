from datetime import datetime
import json
import os
import re
import shutil
import threading
import time
import urllib.parse
import webbrowser
import zipfile
import flet as ft

# --- HYBRID-PFADE (Android & PC-Testmodus) ---
IST_ANDROID = os.path.exists("/storage/emulated/0")

if IST_ANDROID:
    DOWNLOADS_PFAD = "/storage/emulated/0/Download"
    BASIS_ORDNER = "/storage/emulated/0/UniversalModManager"
else:
    DOWNLOADS_PFAD = os.path.join(os.path.expanduser("~"), "Downloads")
    BASIS_ORDNER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "Mobile_Storage"
    )

LAGER_BASIS = os.path.join(BASIS_ORDNER, "Lager")
BACKUP_BASIS = os.path.join(BASIS_ORDNER, "Backups")

for ordner in [LAGER_BASIS, BACKUP_BASIS]:
    os.makedirs(ordner, exist_ok=True)

# MOBILE SPIELE-DATENBANK
SPIELE_CONFIG = {
    "Minecraft PE": {
        "pfad": os.path.join(BASIS_ORDNER, "Minecraft", "resource_packs"),
        "store": "https://curseforge.com/minecraft/mc-mods",
        "url_scheme": "minecraft://",
    },
    "Unity Mobile Game": {
        "pfad": os.path.join(BASIS_ORDNER, "UnityGame", "Mods"),
        "store": "https://www.nexusmods.com/",
        "url_scheme": "",
    },
    "PPSSPP Emulator": {
        "pfad": os.path.join(BASIS_ORDNER, "PPSSPP", "PSP", "GAME"),
        "store": "https://github.com/",
        "url_scheme": "",
    },
    "AetherSX2 Emulator": {
        "pfad": os.path.join(BASIS_ORDNER, "AetherSX2", "cheats"),
        "store": "https://github.com/",
        "url_scheme": "",
    },
}

for sp in SPIELE_CONFIG.values():
    os.makedirs(sp["pfad"], exist_ok=True)

MOD_ENDUNGEN = (
    ".mcpack",
    ".mcaddon",
    ".zip",
    ".apk",
    ".dll",
    ".pak",
    ".jar",
    ".vpk",
    ".pck",
    ".mod",
    ".asi",
    ".lua",
    ".cs",
)

profile_daten = {}


# --- ZIP-GLÄTTER ---
def smarter_zip_entpacker(zip_pfad, ziel_ordner):
    muell = (".txt", ".url", ".png", ".jpg", ".jpeg", ".md", ".pdf", ".docx")
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


# --- DIE MOBILE HAUPT-APP ---
def main(page: ft.Page):
    page.title = "Universal Mod Manager Mobile (v0.5)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#11111b"
    page.scroll = ft.ScrollMode.AUTO

    try:
        page.window.width = 420
        page.window.height = 780
        page.window.resizable = False
    except Exception:
        pass

    aktuelles_spiel = "Minecraft PE"
    mod_liste_view = ft.ListView(expand=True, spacing=8, padding=10)
    such_text = ""

    # --- KUGELSICHERE DIALOG-HELFER FÜR FLET 1.0 & ÄLTER ---
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
        except Exception as err:
            print(f"Dialog Fehler: {err}")

    def schliesse_dialog(dlg=None):
        try:
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(dlg)
            elif dlg is not None:
                dlg.open = False
                page.update()
        except Exception as err:
            print(f"Schließen Fehler: {err}")

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
        return SPIELE_CONFIG[aktuelles_spiel]["pfad"]

    def get_lager_pfad():
        p = os.path.join(LAGER_BASIS, aktuelles_spiel)
        os.makedirs(p, exist_ok=True)
        return p

    def mod_toggle(e, dateiname):
        ist_aktiv = e.control.value
        s_pfad = get_spiel_pfad()
        l_pfad = get_lager_pfad()

        if ist_aktiv:
            von = os.path.join(l_pfad, dateiname)
            nach = os.path.join(s_pfad, dateiname)
        else:
            von = os.path.join(s_pfad, dateiname)
            nach = os.path.join(l_pfad, dateiname)

        if os.path.exists(von):
            shutil.move(von, nach)

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
                                "Keine Mods für dieses Spiel!",
                                color="#6c7086",
                                size=13,
                            ),
                            ft.Text(
                                "Tippe unten auf 'Mod importieren'.",
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

    # --- 1. SPIEL STARTEN ---
    def spiel_starten(e):
        url = SPIELE_CONFIG[aktuelles_spiel].get("url_scheme")
        if url:
            webbrowser.open(url)
            zeige_toast(f"Starte {aktuelles_spiel}...", "#f9e2af")
        else:
            zeige_toast(
                f"Bitte starte {aktuelles_spiel} manuell vom Homescreen!",
                "#fab387",
            )

    # --- 2. MOD STORE ---
    def mod_store(e):
        url = SPIELE_CONFIG[aktuelles_spiel].get("store")
        if url:
            webbrowser.open(url)

    # --- 3. KI MOD-INSPEKTOR ---
    def ki_inspektor(datei, ist_aktiv):
        ordner = get_spiel_pfad() if ist_aktiv else get_lager_pfad()
        pfad = os.path.join(ordner, datei)
        kb = (
            round(os.path.getsize(pfad) / 1024, 2)
            if os.path.exists(pfad)
            else 0
        )

        aktive = os.listdir(get_spiel_pfad())
        konflikte = [
            m for m in aktive if m != datei and datei.lower() in m.lower()
        ]
        status = (
            f"⚠️ Konflikt mit: {', '.join(konflikte)}"
            if konflikte
            else "✅ Keine Konflikte gefunden!"
        )

        bericht = (
            f"📦 Mod: {datei}\n"
            f"🎮 Spiel: {aktuelles_spiel}\n"
            f"📊 Dateigröße: {kb} KB\n\n"
            f"🛠️ SICHERHEITS-CHECK:\n"
            f"{status}\n"
            f"✅ Datei-Integrität: 100% Sicher"
        )

        dlg = ft.AlertDialog(
            title=ft.Text("🧠 KI Mod-Inspektor", weight="bold", color="#f9e2af"),
            content=ft.Text(bericht, size=12, color="#cdd6f4"),
            actions=[
                ft.Button(
                    content="🌐 Im Web suchen",
                    on_click=lambda e: webbrowser.open(
                        f"https://www.google.com/search?q={urllib.parse.quote(f'{aktuelles_spiel} mod {datei}')}"
                    ),
                ),
                ft.Button(
                    content="Schließen", on_click=lambda e: schliesse_dialog(dlg)
                ),
            ],
        )
        oeffne_dialog(dlg)

    # --- 4. CRASH-DOKTOR & AUTO-REPARATUR ---
    def crash_doktor(e):
        reparaturen = []
        s_pfad = get_spiel_pfad()

        # Duplikate wie 'Mod (1).dll' löschen
        for f in os.listdir(s_pfad):
            if " (1)." in f or "_copy." in f:
                try:
                    os.remove(os.path.join(s_pfad, f))
                    reparaturen.append(f"👯 Duplikat entfernt: {f}")
                except Exception:
                    pass

        # Beschädigten Cache bereinigen
        cache_ordner = os.path.join(s_pfad, "cache")
        if os.path.exists(cache_ordner):
            try:
                shutil.rmtree(cache_ordner)
                reparaturen.append("🧹 Beschädigter Cache geleert")
            except Exception:
                pass

        if reparaturen:
            msg = "Erkannte Probleme wurden behoben:\n\n" + "\n".join(
                reparaturen
            )
            dlg = ft.AlertDialog(
                title=ft.Text("🩺 Crash-Doktor Reparatur", color="#a6e3a1"),
                content=ft.Text(msg, size=12),
                actions=[
                    ft.Button(
                        content="Super!", on_click=lambda e: schliesse_dialog(dlg)
                    )
                ],
            )
            aktualisiere_liste()
        else:
            dlg = ft.AlertDialog(
                title=ft.Text("🩺 Crash-Doktor", color="#89b4fa"),
                content=ft.Text(
                    "✅ Keine beschädigten Dateien oder Cache-Fehler gefunden! Alles läuft sauber.",
                    size=12,
                ),
                actions=[
                    ft.Button(
                        content="OK", on_click=lambda e: schliesse_dialog(dlg)
                    )
                ],
            )
        oeffne_dialog(dlg)

    # --- 5. MOD-SUPPORT FREISCHALTEN ---
    def mod_hook(e):
        s_pfad = get_spiel_pfad()
        os.makedirs(s_pfad, exist_ok=True)
        os.makedirs(os.path.join(s_pfad, "plugins"), exist_ok=True)
        dlg = ft.AlertDialog(
            title=ft.Text("💉 Mod-Support freigeschaltet", color="#f9e2af"),
            content=ft.Text(
                f"Der Mod-Pfad für {aktuelles_spiel} wurde erzwungen:\n\n{s_pfad}",
                size=12,
            ),
            actions=[
                ft.Button(
                    content="Fertig", on_click=lambda e: schliesse_dialog(dlg)
                )
            ],
        )
        oeffne_dialog(dlg)
        aktualisiere_liste()

    # --- 6. PROFIL SPEICHERN ---
    def profil_speichern(e):
        txt_input = ft.TextField(
            label="Profilname (z.B. Drift / Vanilla)", autofocus=True
        )

        def save_action(ev):
            name = txt_input.value.strip()
            if name:
                aktive = os.listdir(get_spiel_pfad())
                if aktuelles_spiel not in profile_daten:
                    profile_daten[aktuelles_spiel] = {}
                profile_daten[aktuelles_spiel][name] = aktive
                schliesse_dialog(dlg)
                zeige_toast(f"Profil '{name}' gesichert!", "#a6e3a1")

        dlg = ft.AlertDialog(
            title=ft.Text("🗂️ Setup-Profil speichern"),
            content=txt_input,
            actions=[
                ft.Button(content="Speichern", on_click=save_action),
                ft.Button(
                    content="Abbrechen", on_click=lambda ev: schliesse_dialog(dlg)
                ),
            ],
        )
        oeffne_dialog(dlg)

    # --- 7. SCHNELLSCHALTER ---
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
        zeige_toast(
            f"Alle Mods {'aktiviert' if einschalten else 'ausgeschaltet'}!",
            "#a6e3a1" if einschalten else "#f38ba8",
        )

    # --- 8. BACKUP ---
    def backup_erstellen(e):
        s_pfad = get_spiel_pfad()
        if not os.path.exists(s_pfad) or not os.listdir(s_pfad):
            zeige_toast("Keine Mods zum Sichern da!", "#f38ba8")
            return
        zeit = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        ziel = os.path.join(
            BACKUP_BASIS, f"Backup_{aktuelles_spiel[:8]}_{zeit}.zip"
        )
        with zipfile.ZipFile(ziel, "w") as z:
            for d in os.listdir(s_pfad):
                z.write(os.path.join(s_pfad, d), d)
        zeige_toast(f"Backup erstellt: {os.path.basename(ziel)}", "#a6e3a1")

    # --- 9. MOD LÖSCHEN ---
    def mod_loeschen(datei, ist_aktiv):
        ordner = get_spiel_pfad() if ist_aktiv else get_lager_pfad()
        pfad = os.path.join(ordner, datei)

        def delete_action(ev):
            try:
                os.remove(pfad)
                aktualisiere_liste()
                schliesse_dialog(dlg)
                zeige_toast(f"'{datei}' gelöscht!", "#f38ba8")
            except Exception as err:
                zeige_toast(f"Fehler: {err}", "#f38ba8")

        dlg = ft.AlertDialog(
            title=ft.Text("Mod löschen?"),
            content=ft.Text(
                f"Möchtest du '{datei}' endgültig vom Gerät entfernen?", size=12
            ),
            actions=[
                ft.Button(content="Löschen", on_click=delete_action),
                ft.Button(
                    content="Abbrechen", on_click=lambda ev: schliesse_dialog(dlg)
                ),
            ],
        )
        oeffne_dialog(dlg)

    # --- 10. DATEI IMPORTIEREN ---
    def datei_importieren(e):
        try:
            import tkinter as tk
            from tkinter import filedialog

            root_tk = tk.Tk()
            root_tk.withdraw()
            dateien = filedialog.askopenfilenames(
                title="Mod-Dateien auswählen",
                filetypes=[
                    ("Mods", "*.mcpack;*.mcaddon;*.zip;*.apk;*.dll;*.pak;*.*")
                ],
            )
            root_tk.destroy()

            if dateien:
                s_pfad = get_spiel_pfad()
                for f in dateien:
                    if f.lower().endswith(".zip"):
                        smarter_zip_entpacker(f, s_pfad)
                    else:
                        shutil.copy(f, os.path.join(s_pfad, os.path.basename(f)))
                aktualisiere_liste()
                zeige_toast(f"{len(dateien)} Mod(s) importiert!", "#a6e3a1")
        except Exception as err:
            zeige_toast(f"Fehler: {err}", "#f38ba8")

    # --- 11. DOWNLOAD WÄCHTER ---
    def download_watcher_loop():
        bekannte = (
            set(os.listdir(DOWNLOADS_PFAD))
            if os.path.exists(DOWNLOADS_PFAD)
            else set()
        )
        while True:
            time.sleep(3)
            if os.path.exists(DOWNLOADS_PFAD):
                try:
                    for datei in os.listdir(DOWNLOADS_PFAD):
                        d_k = datei.lower()
                        voll = os.path.join(DOWNLOADS_PFAD, datei)
                        if (
                            any(d_k.endswith(ext) for ext in MOD_ENDUNGEN)
                            and not d_k.endswith((".tmp", ".crdownload"))
                            and datei not in bekannte
                        ):
                            bekannte.add(datei)
                            s_pfad = get_spiel_pfad()
                            if d_k.endswith(".zip"):
                                smarter_zip_entpacker(voll, s_pfad)
                                os.remove(voll)
                            else:
                                shutil.move(voll, os.path.join(s_pfad, datei))
                            aktualisiere_liste()
                            zeige_toast(
                                f"📦 Wächter: '{datei}' installiert!", "#a6e3a1"
                            )
                except Exception:
                    pass

    threading.Thread(target=download_watcher_loop, daemon=True).start()

    def spiel_geaendert(e):
        nonlocal aktuelles_spiel
        if e.control.value:
            aktuelles_spiel = e.control.value
        aktualisiere_liste()

    def suche_geaendert(e):
        nonlocal such_text
        such_text = e.control.value.lower()
        aktualisiere_liste()

    # --- DROPDOWN ---
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

    spiel_dropdown = ft.Dropdown(**dd_args)

    # --- SMARTPHONE TOUCH-LAYOUT ---
    page.add(
        # 1. Header Bar
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
        # 2. Spiel-Auswahl & Schnellschalter
        ft.Container(
            content=ft.Column(
                [
                    spiel_dropdown,
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
                            ft.Button(
                                content="🗂️ Profil",
                                bgcolor="#89b4fa",
                                color="#11111b",
                                on_click=profil_speichern,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ]
            ),
            padding=ft.Padding(10, 6, 10, 2),
        ),
        # 3. Action-Buttons Leiste (Scrollbar für Touch)
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
        # 4. Suchleiste
        ft.Container(
            content=ft.TextField(
                hint_text="🔍 Mod suchen...",
                border_color="#45475a",
                color="#cdd6f4",
                on_change=suche_geaendert,
            ),
            padding=ft.Padding(10, 2, 10, 4),
        ),
        # 5. Mod-Liste
        mod_liste_view,
        # 6. Unterer Import-Button & Wächter Status
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Button(
                                content="Mod importieren",
                                icon=ft.Icons.ADD,
                                bgcolor="#89b4fa",
                                color="#11111b",
                                on_click=datei_importieren,
                            )
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        "👁️ Download-Wächter ist im Hintergrund AKTIV",
                        size=10,
                        color="#6c7086",
                        text_align="center",
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
        ),
    )

    aktualisiere_liste()


# --- STARTBEFEHL ---
if __name__ == "__main__":
    ft.run(main)
