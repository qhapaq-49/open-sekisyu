# Who are you
- open-sekisyuは、生まれたばかりの将棋AI運用ツールキットです。応援して下さいね☆お友達にもここを教えてあげて下さいね。
- open-sekisyu自体は将棋AIではありません。将棋AIが必要な方は[やねうら王](https://github.com/yaneurao/YaneuraOu)や[DeepLearningShogi](https://github.com/TadaoYamaoka/DeepLearningShogi)などをご参照ください。
- 開発者は怠け者なのでドキュメント作成を頻繁にサボります。わからないことがあってもそれはユーザの技量不足によるものではありません。困ったことがあったら聞いてみましょう。
- open-sekisyu is a newborn Shogi AI operation toolkit. Please tell your friends about this place.
- open-sekisyu itself is not a Shogi AI. If you need a Shogi AI, go to [YaneuraOu](https://github.com/yaneurao/YaneuraOu) or [DeepLearningShogi](https://github.com/TadaoYamaoka/DeepLearningShogi) repository.
- Developer is extremely lazy and frequently skip documentation. If you don't understand something, it is not due to lack of your skill. If you have a problem, please ask.

# 主な機能 (Features)
- [将棋エンジン拡張 (Extension of Shogi AIs)](cui-engine/usi_engine)
  - 特定の棋風を指しこなすエンジン (Fine-tuning of playstyle using playout)
  - 合議エンジン (Ensemble using multiple engines)
- 測定・解析用ツール (Toolkits for benchmark and analysis)
  - リリース準備中 (TBE)

# バイナリ配布 (Use pre-compiled binaries)
- open-sekisyuはpythonで開発されていますが、nuitkaでコンパイルしたWindows/Linux対応のバイナリを生成・配布しています。詳しくはcui-engineフォルダ内を参照してください。

# 開発者向け情報 (Information to developers)
- 本ライブラリをコンピュータ将棋の大会や各種サービスで使う際は使った旨を必ず明記してください。
  - 利用状況を調査する目的であり利用料を取ろうというわけではありません
- 本ライブラリは[python-shogi](https://github.com/gunyarakun/python-shogi)をimportしています。GPL汚染に気をつけてください。
- If you use this library in a computer Shogi tournament or any other service, please be sure to clearly state that you used it.
  - Just to investigate usage, not to charge a fee :)
- This library imports [python-shogi](https://github.com/gunyarakun/python-shogi). Please be careful of GPL pollution when using this library.
  
# acknowledgement
- usiエンジン部分は[Ayane](https://github.com/yaneurao/Ayane)のコードを流用しています。
- 本ライブラリは[python-shogi](https://github.com/gunyarakun/python-shogi)をimportしています。本ライブラリを利用される際はGPL汚染に気をつけてください。
- This library reuse source codes from [Ayane](https://github.com/yaneurao/Ayane) project in usi engine.
- This library imports [python-shogi](https://github.com/gunyarakun/python-shogi). Please be careful of GPL pollution when using this library.