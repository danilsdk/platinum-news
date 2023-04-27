from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Sequence

# Файл базы данных
database_file = 'data/bot_database.sqlite'

engine = create_engine(f'sqlite:///{database_file}')
Session = sessionmaker(bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    nickname = Column(String)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)


class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, Sequence('news_id_seq'), primary_key=True, autoincrement=True)
    text = Column(String)
    attachment = Column(String)
    type = Column(String)
    source = Column(String)


class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True)
    footer = Column(String)
    header = Column(String)
    lang = Column(String)


Base.metadata.create_all(engine)

# Добавляем запись в таблицу Template
session = Session()
template = Template(footer='', header='', lang='ru')
session.add(template)
session.commit()
session.close()
