const video = document.getElementById('video')
const canvas = document.getElementById('canvas')
const log = document.getElementById('log')
const ctx = canvas.getContext('2d')

// WebSocket 연결
const socket = new WebSocket('wss://' + location.host + '/ws')

socket.onopen = () => {
  console.log('✅ WebSocket 연결됨')
  log.innerText = '🔌 WebSocket 연결됨'
}

socket.onclose = () => {
  console.warn('⚠️ WebSocket 연결 종료됨')
  log.innerText = '❌ WebSocket 연결 종료됨'
}

socket.onerror = (err) => {
  console.error('❌ WebSocket 오류', err)
  log.innerText = '❌ WebSocket 오류 발생'
}

socket.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data)
    const result = data.result

    const now = new Date()
    const timestamp = now.toLocaleTimeString('ko-KR', { hour12: false })

    // 🖌️ 조건별 색상 결정 (한글 상태 대응)
    let bgColor = '#333'
    if (result.sleep_status === '자는 중' || result.sleep_status === 'sleeping')
      bgColor = '#902020'
    else if (result.direction === '등짐' || result.direction === 'back')
      bgColor = '#a55e00'
    else if (result.action === '앉음' || result.action === 'sitting')
      bgColor = '#204080'

    const logEntry = document.createElement('div')
    logEntry.className = 'log-entry'
    logEntry.innerHTML = `
      <div class="log-bubble" style="background-color: ${bgColor}">
        <strong>[${timestamp}]</strong><br>
        📍 방향: <b>${result.direction}</b><br>
        🧍 자세: <b>${result.action}</b><br>
        💤 상태: <b>${result.sleep_status}</b><br>
        🧿 EAR: <b>${result.ear}</b>
      </div>
    `
    log.appendChild(logEntry)
    log.scrollTop = log.scrollHeight

    // ✅ EAR 그래프 업데이트
    if (result.ear !== null && typeof result.ear === 'number') {
      earHistory.push(result.ear)
      if (earHistory.length > maxPoints) earHistory.shift()
      drawGraph()
    }
  } catch (e) {
    console.log('📩 받은 메시지:', event.data)
  }
}

// ✅ 카메라 요청은 1번만 실행
console.log('🟡 페이지 로드됨, 카메라 요청 시작')
// canvas 해상도 고정 (분석 최적화)
//320x240, 480x360, 640x480 중 하나 선택
canvas.width = 480
canvas.height = 360

navigator.mediaDevices
  .getUserMedia({ video: true })
  .then((stream) => {
    console.log('✅ 카메라 스트림 시작')
    alert('✅ 카메라 연결됨')
    video.srcObject = stream

    // 프레임 캡처 및 WebSocket 전송
    setInterval(() => {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob(
        (blob) => {
          if (blob && socket.readyState === 1) {
            blob.arrayBuffer().then((buf) => {
              socket.send(buf)
            })
          }
        },
        'image/jpeg',
        0.8 // 최적의 JPEG 품질
      )
    }, 500) // 0.5초 간격
  })
  .catch((err) => {
    console.error('❌ 카메라 접근 실패', err)
    alert('❌ 카메라 접근 실패: ' + err.message)
    log.innerText = '❌ 카메라 접근 실패: ' + err.message
  })

// 그래프 관련 설정
const chart = document.getElementById('earChart')
const chartCtx = chart.getContext('2d')

const earHistory = []
const maxPoints = 50
const thresh = 0.3 // server.py 에서 사용 중인 SLEEP_EAR_THRESH와 일치시켜야 함

function drawGraph() {
  chartCtx.clearRect(0, 0, chart.width, chart.height)

  // 기준선 (EAR 임계값)
  const threshY = chart.height * (1 - thresh)
  chartCtx.strokeStyle = '#444'
  chartCtx.beginPath()
  chartCtx.moveTo(0, threshY)
  chartCtx.lineTo(chart.width, threshY)
  chartCtx.stroke()

  // EAR 선 그래프
  chartCtx.strokeStyle = '#00eaff'
  chartCtx.beginPath()
  earHistory.forEach((v, i) => {
    const x = (i / maxPoints) * chart.width
    const y = chart.height * (1 - v)
    if (i === 0) chartCtx.moveTo(x, y)
    else chartCtx.lineTo(x, y)
  })
  chartCtx.stroke()
}
