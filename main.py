import bs4
import requests
import os
from urllib.parse import quote_plus
from beaupy import select_multiple, spinners, prompt
from rich import console
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import traceback
import zipfile
import re
from time import perf_counter
import sys
import dotenv
rmr = '​'*30
dotenv.load_dotenv()
subject = "Kindle book"
sender = os.getenv('EMAIL_ADDRESS')
recipient = os.getenv('KINDLE_ADDRESS')
password = os.getenv('PASSWORD_EMAIL')
email_server = os.getenv('EMAIL_SERVICE'), int(os.getenv('EMAIL_PORT'))

def send_email(subject, sender, recipient, password, attachment_path):
    # Create the email message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient


    with open(attachment_path, 'rb') as attachment_file:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_file.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={os.path.split(attachment_path)[-1]}',
        )
        msg.attach(part)

    # Send the email
    with smtplib.SMTP_SSL(*email_server) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipient, msg.as_string())
def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"


def printsep(): print('-'*(os.get_terminal_size().columns-70))
debug = False
def downloadlink(page):
    page_2 = requests.get('https://libgen.li/'+page)
    bs2 = bs4.BeautifulSoup(page_2.text, 'lxml')
    download_page = bs2.select_one('#tablelibgen > tr > td.valign-middle > a').attrs['href']
    urldirect = True
    try:
        page_3 = requests.get('https://libgen.li'+download_page, timeout=3)
        if page_3.content.lower().startswith(b'<!doc'):
            bs3 = bs4.BeautifulSoup(page_3.text, 'lxml')
            downurl = 'https://libgen.li/'+bs3.select_one('#main > tr:nth-child(1) > td:nth-child(2) > a').attrs['href']
            urldirect = False
    except: pass
    if urldirect:
        downurl = 'https://libgen.li'+download_page
    return downurl
def dbg(*values: object, sep: str | None = ' ', end: str | None = '\n'):
    if debug:
        print(*values, sep=sep, end=end)
def search(query: str):
    selector = '#tablelibgen > tbody tr'
    page = requests.get(f'https://libgen.li/index.php?req={quote_plus(query)}&columns%5B%5D=t&columns%5B%5D=a&columns%5B%5D=s&columns%5B%5D=y&columns%5B%5D=p&columns%5B%5D=i&objects%5B%5D=f&objects%5B%5D=e&objects%5B%5D=s&objects%5B%5D=a&objects%5B%5D=p&objects%5B%5D=w&topics%5B%5D=l&topics%5B%5D=c&topics%5B%5D=f&topics%5B%5D=s&res=25&covers=on&filesuns=all&columns%5B%5D=t&columns%5B%5D=a&columns%5B%5D=s&columns%5B%5D=y&columns%5B%5D=p&columns%5B%5D=i&objects%5B%5D=f&objects%5B%5D=e&objects%5B%5D=s&objects%5B%5D=a&objects%5B%5D=p&objects%5B%5D=w&topics%5B%5D=l&topics%5B%5D=c&topics%5B%5D=f&topics%5B%5D=s&res=100&covers=on&filesuns=all')
    bs = bs4.BeautifulSoup(page.text, 'lxml')
    manga = []
    elems = bs.select(selector)
    for elem in elems:
        try:
            #cover_url = 'https://libgen.li' + elem.select_one('td:nth-child(1) > a > img').attrs['src']
            title = elem.select_one('td:nth-child(2) b').text.strip()
            url = elem.select_one('td:nth-child(2) > a:nth-child(3)').attrs['href']
            series = elem.select_one('td:nth-child(2) > a:nth-child(3)').text.strip()

            if debug: printsep()
            #dbg(f'{cover_url=}')
            dbg(f'{title=}')
            dbg(f'{url=}')
            dbg(f'{series=}')
            manga.append((series, title, url))
        except AttributeError: continue
    return manga
def calculate_remaining_time(downloaded, secondstodown, downed, size):
    # Calculate download speed in bytes per second
    speed_bytes_per_second = downed / secondstodown
    
    # Calculate the amount of data left to download
    remaining_data = size - downloaded
    
    # Calculate the remaining time in seconds
    if speed_bytes_per_second > 0:
        remaining_time_seconds = remaining_data / speed_bytes_per_second
    else:
        return '?m ?s'

    # Convert seconds to minutes and seconds
    minutes = int(remaining_time_seconds // 60)
    seconds = int(remaining_time_seconds % 60)

    return f"{minutes}m {seconds}s"
cs = console.Console()
cs.print('[pink1]Enter search query[/pink1] [bold white]::[/] ', end='')
query = input('')

manga = search(query)
if len(manga) < 1:
    cs.print('[red1] ✖  Didn\'t find anything.[/red1]')
    subprocess.run([sys.executable]+sys.argv)
    exit()

items = [f'{info[1]} ({info[0]})' for info in manga]
selected_items = select_multiple(items, tick_character=' ✓ ', pagination=True, page_size=7, minimal_count=1)
selected = []
poss = {}
for sel in selected_items:
    if not sel in poss:
        poss[sel] = 0
    onlytitles = [info for info in manga if f'{info[1]} ({info[0]})' == sel]
    selected.append(onlytitles[poss[sel]])
    poss[sel] += 1
#cs.print('[pink1]Enter folder where to save manga[/pink1] [bold white]::[/] ', end='')
#dir_ = input('')
dir_ = 'manga'
threads = []
supported = ['epub', 'pdf', 'doc', 'docx', 'htm', 'html', 'rtf', 'txt', 'jpg', 'gif', 'bmp', 'png']
def geteta(down, size, estimated_remaining_time=None):
    status = f"[pink1]Downloading [/pink1] [white bold]{format_bytes(down)}/{format_bytes(size)}"
    if estimated_remaining_time is not None:
        status += f" (ETA: {estimated_remaining_time:.2f}s)"
    status += '[/]'
    print(status, end='\r')
os.makedirs(dir_, exist_ok=True)
for info in selected:
    existing = os.listdir(dir_)
    def downloadit(info):
        try:
            path = None
            link = downloadlink(info[2])
            files = [os.path.join(dir_, file) for file in existing if '.'.join(file.split('.')[:-1]) == f'{info[1]} ({info[0]})'.translate({ord(c): None for c in '\\/:*?"\'<>|'})]
            if len(files) > 0:
                for f in files:
                    ftype = os.path.split(f)[-1].split('.')[-1]
                    if ftype in supported:
                        cs.print('[pink1 bold]Found manga in cache![/]')
                        path = f
                        break
            if not path:
                path = os.path.join(dir_, f'{info[1]} ({info[0]})'.translate({ord(c): None for c in '\\/:*?"\'<>|'}))
                cs.print('[pink1]Downloading [/pink1] [white bold]0/0[/] (?m ?s)', end='\r')
                down = 0
                
                with requests.get(link, stream=True) as r:
                    dbg('entered stream')
                    r.raise_for_status()
                    dbg('raised for status ended')
                    size = int(r.headers.get('Content-Length'))
                    cdhead = r.headers.get('Content-Disposition')
                    ftype = cdhead.split('.')[-1].split('"')[0]
                    dbg('content-dispotition:', cdhead, 'file ext:',ftype)
                    path += '.'+ftype
                    
                    with open(path, 'wb') as f:
                        lasttime = perf_counter()
                        for chunk in r.iter_content(chunk_size=9048):
                            newtime = perf_counter()
                            down += len(chunk)
                            f.write(chunk)
                            cs.print(f'[pink1]Downloading [/pink1] [white bold]{format_bytes(down)}/{format_bytes(size)} ({calculate_remaining_time(down, newtime-lasttime, len(chunk), size)})[/]'+rmr, end='\r')
                            lasttime = perf_counter()
        except Exception as e:
            if e.__class__ is requests.exceptions.HTTPError:
                cs.print('[red1] ✖  Site errored out, trying again...[/red1]'+rmr)
            else:
                cs.print(f'[red1] ✖  Unknown error. Traceback :: '+rmr)
                trace = traceback.format_exc()
                trace = '\n   '.join(trace.split('\n')[1:])
                cs.print(f'[red1]{trace}[/]')
                exit()
            return downloadit(info)
        return ftype, path
    ftype, path = downloadit(info)
    dbg(path)
    cs.print('[pink1 bold] [ ✓ ] Downloaded/got from cache [/]'+rmr)
    if not ftype in supported:
        spin = spinners.Spinner(['[pink1 bold]Converting book to epub...[/]'+'[pink1]'+x+'[/]' for x in spinners.DOTS], '')
        spin.start()
        mobi = os.path.join(dir_, f'{info[1]} ({info[0]}).epub'.translate({ord(c): None for c in '\\/:*?"\'<>|'}))
        
        subprocess.run(['ebook-convert', path, mobi], stdout=subprocess.PIPE)
        spin.stop()
        cs.print('[pink1 bold] [ ✓ ] Converted book to epub [/]')
    else:
        mobi = path
    spin = spinners.Spinner(['[pink1 bold]Zipping[/] '+'[pink1]'+x+'[/]' for x in spinners.DOTS], '')
    spin.start()
    with zipfile.ZipFile('book.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=8) as zipf:
        zipf.write(mobi)
    spin.stop()
    cs.print('[pink1 bold] [ ✓ ] Zipped book succesfully[/]')
    spin = spinners.Spinner(['[pink1]Sending email to Kindle[/pink1] '+'[pink1]'+x+'[/]' for x in spinners.DOTS], '')
    spin.start()
    send_email(subject, sender, recipient, password, 'book.zip')
    spin.stop()
    cs.print('[pink1 bold] [ ✓ ] Sent email to Kindle![/]')

