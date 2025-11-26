# nomikai_planner_app.py

import logging
from typing import Optional

import streamlit as st
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException
from strands import Agent, tool

# ========== ログ設定 ==========
logging.getLogger("strands").setLevel(logging.INFO)

# ========== Web検索ツール定義 ==========

@tool
def websearch(keywords: str, region: str = "jp-ja", max_results: Optional[int] = 5) -> str:
    """
    DuckDuckGo を用いて Web 検索をします。
    検索結果のタイトル・URL・概要を日本語のテキストで返します。
    """
    try:
        results = list(DDGS().text(keywords, region=region, max_results=max_results))
        if not results:
            return "検索結果が見つかりませんでした。"

        lines: list[str] = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "")
            url = r.get("href") or r.get("link") or ""
            body = r.get("body") or r.get("description") or ""
            lines.append(
                f"{i}. {title}\nURL: {url}\n概要: {body}"
            )

        return "\n\n".join(lines)

    except RatelimitException:
        return "DuckDuckGo のレート制限に達しました。しばらく待ってから再試行してください。"
    except DDGSException as d:
        return f"DuckDuckGo 検索でエラーが発生しました: {d}"
    except Exception as e:
        return f"不明なエラーが発生しました: {e}"


# ========== Strands Agent 定義 ==========

agent = Agent(
    # ここはあなたの環境のモデルに合わせて変更してください
    # 例: "bedrock:anthropic.claude-3-5-sonnet-20240620-v1:0"
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",

    system_prompt=(
        "あなたはプロの飲み会プランナーです。"
        "ユーザーが提示した条件に対して、最適なお店を提案して下さい。"
        "参加者の年齢層や人数やどのような集まりなのかを考慮し、"
        "カジュアルな友人との飲み会から、フォーマルな仕事付き合いの飲み会まで、"
        "状況に応じて最適なお店を考えてください。"
        "必要に応じて websearch ツールを使用し、候補となるお店名・平均的な金額・URL をまとめてください。"
        "返答は必ず日本語で行ってください。"
    ),
    tools=[websearch],
)


# ========== Streamlit アプリ ==========

def build_prompt(
    area: str,
    datetime_text: str,
    group_desc: str,
    budget: str,
    mood: str,
) -> str:
    """
    フォーム入力から、Agent に渡すプロンプトを組み立てる。
    """
    return (
        "以下の条件で懇親会のお店を提案してください。\n\n"
        f"・お店のエリア: {area}\n"
        f"・日時: {datetime_text}\n"
        f"・どんな集まりか: {group_desc}\n"
        f"・1人当たりの予算: {budget}\n"
        f"・お店の雰囲気: {mood}\n\n"
        "条件に合いそうなお店を、できれば複数候補挙げてください。\n"
        "それぞれについて、想定される1人あたりの金額の目安と、お店のURLも示してください。\n"
        "必要であれば websearch ツールを呼び出して、実在するお店を検索して構いません。"
    )


def main():
    st.set_page_config(page_title="懇親会お店プランナー", page_icon="🍻")
    st.title("🍻 懇親会お店プランナー（StrandsAgents＋Web検索）")

    st.markdown(
        "以下の条件を入力すると、AI が DuckDuckGo 検索ツールを使いながら、"
        "懇親会に最適なお店を提案します。"
    )

    with st.form("nomikai_form"):
        area = st.text_input("お店のエリア", placeholder="例: 東京駅周辺、渋谷、新宿")
        datetime_text = st.text_input("日時", placeholder="例: 2025/12/10 19:00〜")
        group_desc = st.text_area(
            "どんな集まりか",
            placeholder="例: 部署の歓送迎会 / プロジェクト打ち上げ / 取引先との会食 など",
        )
        budget = st.text_input(
            "1人当たりの予算（円）",
            placeholder="例: 4000〜6000",
        )
        mood = st.text_input(
            "お店の雰囲気",
            placeholder="例: 落ち着いた、にぎやか、おしゃれ、個室あり など",
        )

        submitted = st.form_submit_button("この条件でお店を提案してもらう")

    if submitted:
        # 入力チェック（簡易）
        if not all([area, datetime_text, group_desc, budget, mood]):
            st.error("すべての項目を入力してください。")
            return

        # Agent に渡すプロンプトを作成
        prompt = build_prompt(area, datetime_text, group_desc, budget, mood)

        st.markdown("### ⏳ AI がプランを検討中…")

        with st.spinner("条件に合うお店を検索しています…"):
            try:
                response = agent(prompt)
            except Exception as e:
                st.error(f"Agent 実行中にエラーが発生しました: {e}")
                return

        st.markdown("### ✅ 提案結果")
        st.write(str(response))


if __name__ == "__main__":
    main()