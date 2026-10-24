import sys
import zipfile
from pathlib import Path

BOOKS = [
    ("alexander_pushkin", "Александр", "Пушкин", "Сказка о рыбаке и рыбке", "poetry",
     "Сказка о старике с золотой рыбкой."),
    ("nikolai_gogol", "Николай", "Гоголь", "Шинель", "prose_contemporary",
     "История о бедном Акакии Акакиевиче."),
    ("mikhail_lermontov", "Михаил", "Лермонтов", "Мцыри", "poetry",
     "Поэма о юном горце, бежавшем из плена."),
    ("ivan_turgenev", "Иван", "Тургенев", "Муму", "prose_contemporary",
     "Рассказ о глухонемом дворнике Герасиме."),
]

ZIP_BOOKS = [
    ("anton_chekhov", "Антон", "Чехов", "Хамелеон", "prose_contemporary",
     "Рассказ о полицейском надзирателе Очумелове."),
    ("leo_tolstoy", "Лев", "Толстой", "Кавказский пленник", "prose_rus_classic",
     "Рассказ о Жилине и Костылине."),
]


def fb2(first_name, last_name, title, genre, annotation, body):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
<description>
 <title-info>
  <genre>{genre}</genre>
  <author>
   <first-name>{first_name}</first-name>
   <last-name>{last_name}</last-name>
  </author>
  <book-title>{title}</book-title>
  <annotation><p>{annotation}</p></annotation>
  <lang>ru</lang>
 </title-info>
 <document-info>
  <author>
   <nickname>sopds-testdata</nickname>
  </author>
  <program-used>sopds scripts/make_testbooks.py</program-used>
  <date>2026-10-24</date>
  <id>urn:uuid:sopds-test-{title.lower().replace(' ', '-')}</id>
  <version>1.0</version>
 </document-info>
</description>
<body>
 <title><p>{title}</p></title>
<p>{title}. {annotation}</p>
<p>{body}</p>
</body>
</FictionBook>
"""


def main(target_dir):
    root = Path(target_dir)
    root.mkdir(parents=True, exist_ok=True)

    for slug, first, last, title, genre, annotation in BOOKS:
        (root / f"{slug}.fb2").write_text(
            fb2(first, last, title, genre, annotation, f"Полный текст {title} недоступен." " Тестовые данные."),
            encoding="utf-8",
        )

    with zipfile.ZipFile(root / "sopds_anthology.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for slug, first, last, title, genre, annotation in ZIP_BOOKS:
            zf.writestr(
                f"{slug}.fb2",
                fb2(first, last, title, genre, annotation, f"Полный текст {title} недоступен." " Тестовые данные."),
            )

    print(f"generated {len(BOOKS)} fb2 files and 1 zip with {len(ZIP_BOOKS)} fb2 files in {root}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "testdata")
