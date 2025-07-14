from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
import numpy as np
import cv2
import mediapipe as mp
import math

app = FastAPI()

# MediaPipe 초기화
mp_pose = mp.solutions.pose
mp_face = mp.solutions.face_mesh
pose = mp_pose.Pose(model_complexity=1)
face_mesh = mp_face.FaceMesh(static_image_mode=False, max_num_faces=1)

# 눈 인덱스
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# 상태 저장 변수
sleep_frame_count = 0
sleeping = False
SLEEP_EAR_THRESH = 0.3 #눈감은거 임계값
SLEEP_CONSEC_FRAMES = 8

# ------------------------ 분석 함수 ------------------------

def euclidean(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def compute_ear(eye):
    A = euclidean(eye[1], eye[5])
    B = euclidean(eye[2], eye[4])
    C = euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def estimate_action(landmarks):
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_hip = landmarks[23]
    right_hip = landmarks[24]
    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    hip_y = (left_hip.y + right_hip.y) / 2
    return "sitting" if (hip_y - shoulder_y) > 0.25 else "standing"

def estimate_direction(face_detected, pose_landmarks):
    if not face_detected:
        return "back"
    nose_x = pose_landmarks[0].x
    left_ear_x = pose_landmarks[7].x
    right_ear_x = pose_landmarks[8].x
    center_diff = abs(nose_x - (left_ear_x + right_ear_x) / 2)
    ear_diff = abs(left_ear_x - right_ear_x)
    if center_diff < 0.02 and ear_diff > 0.1:
        return "front"
    elif nose_x < left_ear_x and nose_x < right_ear_x:
        return "right side"
    elif nose_x > left_ear_x and nose_x > right_ear_x:
        return "left side"
    return "unknown"

def analyze_frame(image):
    global sleep_frame_count, sleeping

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results_pose = pose.process(rgb)
    results_face = face_mesh.process(rgb)

    direction = "알 수 없음"
    action = "알 수 없음"
    sleep_status = "깨어있음"
    ear_avg = None

    if results_pose.pose_landmarks:
        landmarks = results_pose.pose_landmarks.landmark
        face_detected = results_face.multi_face_landmarks is not None

        dir_en = estimate_direction(face_detected, landmarks)
        direction = {
            "front": "정면",
            "back": "등짐",
            "right side": "오른쪽 측면",
            "left side": "왼쪽 측면"
        }.get(dir_en, "알 수 없음")

        act_en = estimate_action(landmarks)
        action = {
            "sitting": "앉음",
            "standing": "서있음"
        }.get(act_en, "알 수 없음")

    # 졸음 판별
    prev_sleeping = sleeping

    if results_face.multi_face_landmarks:
        face_landmarks = results_face.multi_face_landmarks[0].landmark
        left_eye = [face_landmarks[i] for i in LEFT_EYE]
        right_eye = [face_landmarks[i] for i in RIGHT_EYE]
        ear_left = compute_ear(left_eye)
        ear_right = compute_ear(right_eye)
        ear_avg = (ear_left + ear_right) / 2.0

        if ear_avg < SLEEP_EAR_THRESH:
            sleep_frame_count += 1
        else:
            sleep_frame_count = 0

        sleeping = sleep_frame_count >= SLEEP_CONSEC_FRAMES
        sleep_status = "자는 중" if sleeping else "깨어있음"

        if sleeping and not prev_sleeping:
            print("[🟡] 졸기 시작")
        elif not sleeping and prev_sleeping:
            print("[🟢] 다시 깨어남")

        print(f"[DEBUG] EAR: {ear_avg:.3f} | Count: {sleep_frame_count} | 상태: {sleep_status}")

    return {
        "direction": direction,
        "action": action,
        "sleep_status": sleep_status,
        "ear": round(ear_avg, 3) if ear_avg is not None else None
    }

# ------------------------ 라우터 ------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/main.js")
async def get_js():
    return FileResponse("main.js")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            np_img = np.frombuffer(data, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            result = analyze_frame(image)
            await websocket.send_json({
                "message": f"{len(data)} bytes received ✅",
                "result": result
            })

    except WebSocketDisconnect:
        print("❌ WebSocket 연결 종료됨")
