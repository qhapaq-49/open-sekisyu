# 将棋エンジン拡張 (Extension of Shogi AIs)
- 棋風の調整やアンサンブルなどの機能に対応しています。各種エンジンの読み込みはconfig.yamlを介して行われます

# 棋風の調整を行うエンジン (Fine-tuning of playstyle using playout)
- 棋風の調整を行います。以下のような動作原理で動いています。詳細はソースコードや[wcscのpr文章](https://www.apply.computer-shogi.org/wcsc31/appeal/MolQha-/molqha_wcsc2021.pdf)を参照
  - コピーしたい棋風との類似度を定義し、類似度に応じて評価値にボーナスを加えることで特定の序盤形を指させるようにしています。
  - 類似度は自軍側の駒に対して位置が一致した数で定義しています
    - すごく雑なハックですがこのぐらいでも藤井システムとかを指すようになります

# 開発者向け情報 (Information to developers)
- 本ライブラリをコンピュータ将棋の大会や各種サービスで使う際は使った旨を必ず明記してください。
  - 利用状況を調査する目的であり利用料を取ろうというわけではありません
- 本ライブラリは[python-shogi](https://github.com/gunyarakun/python-shogi)をimportしています。GPL汚染に気をつけてください。
- If you use this library in a computer Shogi tournament or any other service, please be sure to clearly state that you used it.
  - Just to investigate usage, not to charge a fee :)
- This library imports [python-shogi](https://github.com/gunyarakun/python-shogi). Please be careful of GPL pollution when using this library.
  