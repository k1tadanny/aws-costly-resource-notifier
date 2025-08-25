# aws-costly-resource-notifier

AWS Configアグリゲーターを使用してマルチアカウントでリソースの存在を通知します。コストの掛かるリソースの消し忘れ防止に活用できます。

## インストール

1. AWSアカウントにAWS Configアグリゲーターを作成します
2. Amazon SNSトピックとサブスクリプションを作成します
3. AWS SAMを使用してSAMテンプレートをデプロイします
   ```sh
   sam deploy --guided --template template.yaml
   ```

## 使い方

デプロイ後は、何もしなくても定期的に通知されます。通知スケジュールはSAMテンプレートに記載されています。
