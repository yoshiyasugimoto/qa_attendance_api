質問チケット・勤怠管理アプリ
====

Overview
質問回数・勤怠の管理をするアプリ

## Description
# 質問チケット関して
このアプリは良い質問ができるようになることを目的に作りました。
ここでいう、良い質問とは

* いい感じの頻度で質問→多すぎず少なすぎず!
* いい感じに調べてから質問→考える力を養おう!

そこで、1回質問すると1枚消費される質問チケットを配布し、一定時間でチケット枚数の回復＆保有上限を設置することで、質問回数を良い感じに制限することにしました。
質問チケットの消費操作はslack上で行えるようにしました。
# 勤怠管理に関して
slackのSlash Commandsと結びつけることでslackによる勤怠の打刻を可能にしました。
また、打刻した情報を全件表示・編集できるように管理画面を作成しました。

## Requirement
requirements.in参照
## Deploy
デプロイ用コマンド
gcloud config set project mlab-apps
gcloud app deploy app.yaml

アプリ起動コマンド
ローカル環境
python app.py test
本番環境
python app.py





