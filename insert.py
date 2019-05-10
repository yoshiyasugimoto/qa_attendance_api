from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import User

engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

user1 = User(id="1", username='yoshiyasugimoto', count=0, attendance=True, is_intern=True)
session.add(user1)

session.add_all([
    User(id="2", username='Satoko Ouchi', count=0, attendance=False, is_intern=True),
    User(id="3", username='Takashima Katsu', count=0, attendance=False, is_intern=True),
    User(id="4", username='Yuki Matsukuma', count=0, attendance=False, is_intern=True),
    User(id="5", username='Yusuke Hamaike', count=0, attendance=False, is_intern=False),
    User(id="6", username='杉本 義弥', count=0, attendance=False, is_intern=True),
    User(id="7", username='Kai Sato', count=0, attendance=False, is_intern=True),
    # User(id=8, username='muraho', count=2, attendance=False, is_intern=False),
    # User(id=9, username='saori murakami', count=2, attendance=False, is_intern=False),
])
session.commit()
session.close()