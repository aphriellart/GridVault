"""GridVault - create an instaloader session from browser cookies (no password).

Run this YOURSELF in your own terminal:
  python ig_session_from_cookie.py <your_instagram_username>

In a browser where you are logged in to instagram.com:
  1. F12 -> Application -> Cookies -> https://www.instagram.com
     -> copy the Value of "sessionid" and paste it when asked (input is hidden).
  2. F12 -> Console -> run:  copy(document.cookie)
     then press Enter in the terminal; this script reads the clipboard itself
     (picks up csrftoken, mid, ...).

The session is saved where instaloader keeps sessions; it grants access to your
account, so never share it or paste cookies anywhere else.
"""
import getpass
import sys
from urllib.parse import unquote

try:
    import instaloader
except ImportError:
    sys.exit("instaloader is not installed. Run: pip install --upgrade instaloader")

IMPORTANT = ("sessionid", "ds_user_id", "csrftoken", "mid", "ig_did", "rur", "datr")


def parse_cookie_string(s: str) -> dict:
    out = {}
    for part in s.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                out[k] = v
    return out


def read_clipboard() -> str:
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        try:
            return r.clipboard_get()
        finally:
            r.destroy()
    except Exception:  # noqa: BLE001
        return ""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python ig_session_from_cookie.py <your_instagram_username>")
    user = sys.argv[1].lstrip("@").strip()

    sessionid = unquote(getpass.getpass("1) Paste the sessionid cookie value (hidden): ").strip())
    if not sessionid or ":" not in sessionid:
        sys.exit("The sessionid is empty/invalid (it usually looks like digits%3A... or digits:...).")
    print("2) Now in the browser: F12 -> Console -> run  copy(document.cookie)")
    cookies = {}
    for _ in range(3):
        input("   then press Enter here (the clipboard is read automatically)... ")
        cookies = parse_cookie_string(read_clipboard())
        if "csrftoken" in cookies:
            break
        print("   The clipboard does not contain Instagram cookies yet (no csrftoken). Try again.")
    else:
        print("   [info] continuing without extra cookies.")
        cookies = {}

    cookies["sessionid"] = sessionid
    cookies.setdefault("ds_user_id", sessionid.split(":")[0])

    L = instaloader.Instaloader(quiet=True)
    jar = L.context._session.cookies
    for k in [k for k in jar.keys() if not jar.get(k)]:
        jar.pop(k, None)  # drop empty default cookies (mid, s_network)
    for k, v in cookies.items():
        jar.set(k, v, domain=".instagram.com", path="/")
    L.context.username = user

    present = [k for k in IMPORTANT if cookies.get(k)]
    missing = [k for k in IMPORTANT if not cookies.get(k)]
    print(f"Cookies captured: {', '.join(present)}")
    if missing:
        print(f"[info] not present: {', '.join(missing)}")

    who = None
    try:
        data = L.context.get_iphone_json("api/v1/accounts/current_user/?edit=true", {})
        who = data.get("user", {}).get("username")
    except Exception as e:  # noqa: BLE001
        print(f"[warning] verification failed: {str(e)[:150]}")
    if who and who.lower() != user.lower():
        print(f"[warning] these cookies belong to @{who}, not @{user}; saving as @{who}.")
        user = who
        L.context.username = who

    L.save_session_to_file()
    status = f"verified as @{who}" if who else "NOT verified (possibly rate limited)"
    print(f"Session saved for @{user} ({status}).")
    print(f"Next, use: --login {user}")


if __name__ == "__main__":
    main()
