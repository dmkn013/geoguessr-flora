# Mac初回返却 PR #1 中央検証・取り込み記録

- PR: https://github.com/dmkn013/geoguessr-flora/pull/1
- 検証対象head: `1cecebb3a6ef5d696d0298bc42edbfb26933bacf`
- merge: `0a310491e693ad67d505f682fede797aae81dd8b`（expected headを指定してmerge成功）
- 割当: `brother-mac-20261028`。12枚・69対象、種以下確定0、ヤシ科1対象、未同定68対象。植物なし1枚。
- 2026-11-04 16:54 JST回に中央Codexが全12枚の元画像全景、必要部位の同比率元画素拡大、全矩形重ね合わせを実表示し、形態記載・不足理由・対象との対応を照合。最初10枚を含む全件を確認。個体分離不能群落と遠景・暗部・ぼけの保留を維持し、国・文字・道路・旧タグ・地理分布を同定根拠にしない。
- 1000402397030790は室内の器具・手元写真で植物が見えず、objects=0と理由を確認。1001789754789899と1002345822275371は全天球全幅と左右端を確認。画像端の木本を別個体数確定に使わない。
- 割当ID、画像ID、原画像SHA256・寸法、schema、中央辞書、completeと全objects.qa_checkedをimporterで検査。全件成功後、4枚ずつ中央目視照合済みの未取込フォルダから--apply。既存中央記録は上書きしない。
- worker原本12件はPR mergeでworker_resultsに保持。中央canonicalのworker_record_sha256、worker_reviewed_at、source_sha256、objectsがGit blob原本と一致することを確認。Windows作業ファイルはGit checkoutによってCRLFとなるためバイトSHAは異なるが、LF正規化後にGit原本と全12件一致。この差を原本不一致や画像ハッシュ不一致と混同しない。今回はgit showから得た原本バイトで取り込んだ。
- 中央reviewed_atとworker日時を分離。割当はimported_image_ids=12、予約継続、未取込8,973枚。原画像、旧タグ、worker原本を削除・書換えしていない。QA画像・切出しはdist/review_work内のローカル確認物。公開deployなし。

| 画像ID | 対象数 | worker Git原本SHA256 | 元画像SHA256 |
| --- | ---: | --- | --- |
| 10000691280060081 | 8 | 5e5e94d5a1c05b009c67703210d31d7d360244cf7d199b7da43521269f4577d4 | e098dc1b49fb3174def5e972d5bb95beafd1dd9c871359534d7839557643281a |
| 1000402397030790 | 0 | 764c0eb8568ea45d2539e0089cc5a8b782e5cfe144b81c2dc0f5c04f8ea5038d | 50a055adb33a2a0734c5bc2cf82796001caa51c4bd5d2ca09dccb6d6a819c87e |
| 1000431968660173 | 10 | 36c36fdf035e68a21dea9ab3e735177ec08d6a873d404f469f2d0a2f66f8d385 | 5150e58852955a08bef12e42aaf90ad87e263e0af592eaf1498cffcf37f00e15 |
| 1000531774774134 | 8 | 6b6d74ee44a90ca8f11f5ead1fb95d0d0590790fd06b0e7e25749b6776253528 | 781aa9d67ef1dff7527651c623133fb91342c7367e9913521896ef58b83bf956 |
| 1000991183771543 | 4 | 24ab4774743740cce5bceaae8a7f2195d27e403f4172df6a5997865663276e48 | 86f45a665942263d3503cafbf43ed49b102feeccca3661e95384c40971300c2f |
| 1001388403792042 | 3 | af26454be5c86c7da322950cb7a4ed10b996e1e753144678a93af9824ffbac56 | 7a6287d92aa415d22e79f7b51fef73922dd5f39b7783ed66150dcc5cba9b5e5d |
| 1001660218545787 | 7 | e6a9816ed4cfad86a156dc037ddd6820f59a62b49c5a88f7a943a4355a731a1f | ecafab5e3bb6c96c337456db4718722abcb789c030487ca00bdbcf1a49a294cf |
| 1001789754789899 | 4 | 36fd1a5390826c0ac61dccabe38364627017b3f6515484b68e40ce7e21910bb2 | 2bcbc484fdc43a4ad82495c34fb1245866a7517d9666247aec72e9cfa612f301 |
| 1002197044693672 | 10 | 7f35b64ed2603f0f383cc3d10856cdea3903f823262a602279efe1a3a47626c5 | 6b1f73c323e16882089d62f8fddb99e0f4449b094e395481246ac765d47a446f |
| 1002231361790588 | 5 | 65c25eda6fe9cd59eab002c3922cae66a7e6aed7fbd3b8927a0016eec077973b | dda360de73ae17ca042045f8dc911f998ebb60c2c8ac785e58cb6923528fa3cc |
| 1002319341854211 | 2 | 07a1b68c729a106445961e163f799fd3e8e8bbb18bcd01e025d7ed2775a4cfd4 | 5d375d97458a1950589de20c0f2d71a56c436fda7b547d68865e39a3b72eb3f3 |
| 1002345822275371 | 8 | 646253920df8c2c8d2bd73e51447b7a07a108524f1eccc04df72e75ce65561a6 | e473b37a0f364a54a57eee26089088d5dc29b33f816bd84f2dd22a2c120a25d8 |
