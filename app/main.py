import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 환경 변수 로드
load_dotenv("../key.env")
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# 이름+주민등록번호 딕셔너리로 불러오기
def load_rrn_dict(filename="rrn_list.txt"):
    rrn_dict = {}
    if not os.path.exists(filename):
        return rrn_dict
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                name, rrn = parts
                rrn_dict[rrn] = name
    return rrn_dict

# 민원 발급 안내 함수
def issue_civil_document(document_type):
    if "주민등록등본" in document_type:
        return json.dumps({
            "document": "주민등록등본",
            "procedure": "신분증을 스캔하고, 수수료를 결제한 뒤 발급 버튼을 눌러주세요."
        })
    elif "가족관계증명서" in document_type:
        return json.dumps({
            "document": "가족관계증명서",
            "procedure": "신분증을 제출하고, 본인 확인 후 발급이 진행됩니다."
        })
    elif "인감증명서" in document_type:
        return json.dumps({
            "document": "인감증명서",
            "procedure": "인감도장 및 신분증을 지참 후, 본인 확인 절차를 거쳐 발급받으세요."
        })
    elif "출입국사실증명서" in document_type:
        return json.dumps({
            "document": "출입국사실증명서",
            "procedure": "여권 또는 신분증을 스캔하고, 화면 안내에 따라 진행하세요."
        })
    else:
        return json.dumps({
            "document": document_type,
            "procedure": "해당 민원서류는 센터에서 직접 문의해 주세요."
        })

# OpenAI function calling용 툴 정의
tools = [
    {
        "type": "function",
        "function": {
            "name": "issue_civil_document",
            "description": "지정된 민원서류의 발급 절차를 안내합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "민원서류 종류, 예: 주민등록등본, 가족관계증명서 등"
                    }
                }
            }
        }
    }
]

def run_kiosk():
    print("행정복지센터 민원발급기입니다. 종료하려면 '종료'를 입력하세요.")
    rrn_dict = load_rrn_dict("rrn_set.txt")

    # 1단계: 민원 종류 파악
    while True:
        user_input = input("어떤 민원서류를 발급받으시겠습니까? (예: 주민등록등본, 가족관계증명서 등)\n사용자: ")
        if user_input.strip() in ["종료", "exit", "quit"]:
            print("민원발급기를 종료합니다.")
            return

        # LLM에게 민원 종류 파악 요청
        messages = [
            {"role": "user", "content": user_input}
        ]
        first_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = first_response.choices[0].message
        tool_calls = getattr(response_message, "tool_calls", None)

        if tool_calls:
            # 민원 종류 파악 성공
            messages.append(response_message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                document_type = function_args["document_type"]

                # 민원 안내문 생성(미리)
                function_response = issue_civil_document(document_type=document_type)
                function_response_obj = json.loads(function_response)
                procedure_msg = function_response_obj.get("procedure", "")

                # 2단계: 주민등록번호 입력 및 이름 확인
                while True:
                    print(f"\n'{document_type}' 민원 발급 절차 안내:")
                    print(f"{document_type} 발급 서비스를 요청하셨네요!")
                    rrn = input("민원 처리를 위해 주민등록번호를 입력해 주세요 (예: 9001011234567):\n사용자: ")
                    if rrn.strip() == "":
                        print("주민등록번호를 반드시 입력해야 민원 처리가 가능합니다.")
                        continue
                    if rrn not in rrn_dict:
                        print("등록된 주민등록번호가 아닙니다. 다시 시도해 주세요.")
                        continue
                    # 이름 인사
                    print(f"{rrn_dict[rrn]}님 안녕하세요!\n")
                    break

                # 3단계: 민원 안내 (최종 응답)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages
                )
                print("\n민원발급기:", final_response.choices[0].message.content)
            break
        else:
            print("민원발급기: 어떤 민원서류를 원하시는지 다시 입력해 주세요.")

if __name__ == "__main__":
    run_kiosk()
