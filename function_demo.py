import os
import sqlite3

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

'''
LabelBase.register(name="CJK", fn_regular="NotoSansCJK-Regular.ttc")
DB_PATH = r"C:\sqlite\Japanese.db"
'''

def resource_path(rel_path: str) -> str:
    # PyInstaller onefile에서 임시폴더(_MEIPASS)로 풀리므로 그 경로를 우선
    base = getattr(__import__("sys"), "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

FONT_PATH = resource_path(os.path.join("fonts", "NotoSansCJK-Regular.ttc"))
LabelBase.register(name="CJK", fn_regular=FONT_PATH)
    
def vbtn(text, on_press, font="CJK"):
    b = Button(text=text, font_name=font, size_hint_y=None, height=50)
    b.bind(on_press=on_press)
    return b

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=12, spacing=12)

        title = Label(text="메인", font_name="CJK", size_hint_y=None, height=40)

        root.add_widget(title)
        root.add_widget(vbtn("단어 저장 화면", self.go_add))
        root.add_widget(vbtn("퀴즈 화면", self.go_quiz))

        self.add_widget(root)

    def go_add(self, _):
        self.manager.current = "add"

    def go_quiz(self, _):
        self.manager.current = "quiz"


class AddScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=12, spacing=12)

        self.status = Label(text="단어 저장", font_name="CJK", size_hint_y=None, height=40)

        self.kanji = TextInput(hint_text="Kanji", multiline=False, font_name="CJK")
        self.reading = TextInput(hint_text="Reading", multiline=False, font_name="CJK")
        self.meaning = TextInput(hint_text="Meaning", multiline=False, font_name="CJK")

        root.add_widget(self.status)
        root.add_widget(self.kanji)
        root.add_widget(self.reading)
        root.add_widget(self.meaning)
        root.add_widget(vbtn("저장", self.on_save))
        root.add_widget(vbtn("메인으로", self.go_main))

        self.add_widget(root)

    def go_main(self, _):
        self.manager.current = "main"

    def on_save(self, _):
        k = self.kanji.text.strip()
        r = self.reading.text.strip()
        m = self.meaning.text.strip()

        if not (k and r and m):
            self.status.text = "오류: 3개 다 입력"
            return

        app = App.get_running_app()
        app.cur.execute(
            "INSERT INTO Japanese (Kanji, Reading, Meaning) VALUES (?, ?, ?)",
            (k, r, m)
        )
        app.conn.commit()

        self.status.text = f"저장 완료: {k}"
        self.kanji.text = ""
        self.reading.text = ""
        self.meaning.text = ""


class QuizScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current = None  # (id, Kanji, Reading, Meaning)

        root = BoxLayout(orientation="vertical", padding=12, spacing=12)

        self.status = Label(text="퀴즈", font_name="CJK", size_hint_y=None, height=40)
        self.question = Label(text="새 문제를 누르세요", font_name="CJK", size_hint_y=None, height=40)

        self.ans_reading = TextInput(hint_text="읽는 법 입력", multiline=False, font_name="CJK")
        self.ans_meaning = TextInput(hint_text="뜻 입력", multiline=False, font_name="CJK")

        root.add_widget(self.status)
        root.add_widget(self.question)
        root.add_widget(self.ans_reading)
        root.add_widget(self.ans_meaning)
        root.add_widget(vbtn("새 문제", self.on_next))
        root.add_widget(vbtn("채점", self.on_check))
        root.add_widget(vbtn("메인으로", self.go_main))

        self.add_widget(root)

    def go_main(self, _):
        self.manager.current = "main"

    def on_next(self, _):
        app = App.get_running_app()
        app.cur.execute("SELECT id, Kanji, Reading, Meaning FROM Japanese ORDER BY RANDOM() LIMIT 1")
        row = app.cur.fetchone()

        if not row:
            self.question.text = "단어가 없음. 먼저 저장해라."
            self.current = None
            return

        self.current = row
        _id, kanji, reading, meaning = row

        self.question.text = f"문제: {kanji}"
        self.status.text = "문제 출제됨"
        self.ans_reading.text = ""
        self.ans_meaning.text = ""

    def on_check(self, _):
        if not self.current:
            self.status.text = "먼저 '새 문제' 눌러라"
            return

        _id, kanji, reading, meaning = self.current
        ans_r = self.ans_reading.text.strip()
        ans_m = self.ans_meaning.text.strip()

        ok_r = (ans_r == reading)
        ok_m = (ans_m == meaning)

        if ok_r and ok_m:
            self.status.text = "정답"
        else:
            self.status.text = f"오답 | 정답: {reading} / {meaning}"


class MyApp(App):
    def build(self):
        # DB 경로(배포 고려하면 user_data_dir 쓰는 게 정석)
        # 지금은 네 경로 그대로 쓰고, 나중에 user_data_dir로 바꾸자.
        db_path = os.path.join(self.user_data_dir, "Japanese.db")
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS Japanese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Kanji TEXT NOT NULL,
            Reading TEXT NOT NULL,
            Meaning TEXT NOT NULL
        )
        """)
        self.conn.commit()

        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(AddScreen(name="add"))
        sm.add_widget(QuizScreen(name="quiz"))
        sm.current = "main"
        return sm

    def on_stop(self):
        try:
            self.conn.close()
        except Exception:
            pass


MyApp().run()