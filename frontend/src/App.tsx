import React, { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { 
  Mic, 
  MicOff, 
  Moon, 
  Sun, 
  Wifi, 
  WifiOff, 
  Volume2, 
  VolumeX,
  Activity,
  Settings,
  ChevronDown
} from 'lucide-react'

// Types for our application state
interface TranscriptionData {
  type: string
  text: string
  timestamp: number
  confidence: number
}

interface AgentStatus {
  status: string
  processing: boolean
}

interface AgentData {
  agents: {
    audio_context: AgentStatus
    translation: AgentStatus
    quality_control: AgentStatus
    voice_synthesis: AgentStatus
  }
  session_id: string
  timestamp: number
}

const languages = [
  { code: 'auto', name: 'Auto-detect' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'ja', name: 'Japanese' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ar', name: 'Arabic' },
  { code: 'hi', name: 'Hindi' },
  { code: 'pt', name: 'Portuguese' },
]

export default function App() {
  // State management
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isTTSEnabled, setIsTTSEnabled] = useState(false)
  const [sourceLanguage, setSourceLanguage] = useState('auto')
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [transcription, setTranscription] = useState('')
  const [translation, setTranslation] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [translationConfidence, setTranslationConfidence] = useState(0)
  const [detectedLanguage, setDetectedLanguage] = useState('--')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [agentData, setAgentData] = useState<AgentData | null>(null)
  const [processingTime, setProcessingTime] = useState('--')
  const [wordsProcessed, setWordsProcessed] = useState(0)

  // WebSocket connections
  const [audioSocket, setAudioSocket] = useState<WebSocket | null>(null)
  const [dashboardSocket, setDashboardSocket] = useState<WebSocket | null>(null)

  // Initialize Electron APIs and WebSocket connections
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Get session ID and backend URL from Electron
        const sessionId = await window.electronAPI?.getSessionId()
        const backendUrl = await window.electronAPI?.getBackendUrl()
        
        if (sessionId) {
          setSessionId(sessionId)
        }

        if (backendUrl) {
          // Connect to audio stream WebSocket
          const audioWsUrl = `${backendUrl.replace('http', 'ws')}/ws/audio-stream/${sessionId}`
          const audioWs = new WebSocket(audioWsUrl)
          
          audioWs.onopen = () => {
            setIsConnected(true)
            console.log('Audio WebSocket connected')
          }
          
          audioWs.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data)
              console.log('Audio WebSocket message:', data)
              
              if (data.type === 'transcription') {
                setTranscription(data.text)
                setConfidence(data.confidence * 100)
                setDetectedLanguage(sourceLanguage === 'auto' ? 'EN' : sourceLanguage.toUpperCase())
                
                // Mock translation for demo
                if (data.text && data.text !== '[Silence]') {
                  setTranslation(`Translated: ${data.text}`)
                  setTranslationConfidence(85)
                  setWordsProcessed(data.text.split(' ').length)
                }
              } else if (data.type === 'audio_chunk') {
                // Handle real audio chunk information
                const audioData = data.audio_data
                const audioMetrics = data.audio_metrics
                
                console.log(`Audio chunk: ${audioData.size_bytes} bytes, Volume: ${audioMetrics.volume_percent.toFixed(1)}%`)
                
                // Update UI based on audio activity
                if (audioMetrics.volume_percent > 10) {
                  // Some audio detected - update detected language with volume indicator
                  const lang = sourceLanguage === 'auto' ? 'EN' : sourceLanguage.toUpperCase()
                  setDetectedLanguage(`${lang} (${audioMetrics.volume_percent.toFixed(0)}%)`)
                }
              } else if (data.type === 'audio_session_started') {
                console.log('Audio session started:', data.config)
                setIsListening(true)
              } else if (data.type === 'audio_session_ended') {
                console.log('Audio session ended:', data.stats)
                setIsListening(false)
              } else if (data.type === 'transcription_result') {
                // Handle Google Cloud transcription results
                const result = data.data
                console.log('Transcription Result:', result)
                
                if (result.transcript && result.transcript.trim()) {
                  setTranscript(result.transcript)
                  
                  // Show translation if available
                  if (result.translation) {
                    setTranslation(result.translation)
                    console.log(`Translation (${result.language_detected} → ${targetLanguage}):`, result.translation)
                  }
                  
                  // Update detected language
                  const lang = result.language_detected || sourceLanguage
                  const confidence = result.confidence ? `${(result.confidence * 100).toFixed(1)}%` : 'N/A'
                  setDetectedLanguage(`${lang.toUpperCase()} (${confidence})`)
                  
                  // Show service and processing info
                  console.log(`Service: ${result.service_type || 'unknown'} | Processing: ${result.processing_time_ms || 0}ms`)
                }
                
                setIsTranscribing(false)
              } else if (data.type === 'error') {
                console.error('Backend error:', data.message)
                setIsListening(false)
                alert(`Audio error: ${data.message}`)
              }
            } catch (error) {
              console.error('Error parsing audio message:', error)
            }
          }
          
          audioWs.onclose = () => {
            setIsConnected(false)
            console.log('Audio WebSocket disconnected')
          }
          
          setAudioSocket(audioWs)

          // Connect to dashboard WebSocket
          const dashboardWsUrl = `${backendUrl.replace('http', 'ws')}/ws/agent-dashboard/${sessionId}`
          const dashboardWs = new WebSocket(dashboardWsUrl)
          
          dashboardWs.onmessage = (event) => {
            const data: AgentData = JSON.parse(event.data)
            setAgentData(data)
          }
          
          setDashboardSocket(dashboardWs)
        }
      } catch (error) {
        console.error('Failed to initialize app:', error)
      }
    }

    initializeApp()

    return () => {
      audioSocket?.close()
      dashboardSocket?.close()
    }
  }, [])

  // Toggle dark mode
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  // Handle start/stop listening
  const toggleListening = async () => {
    if (!isListening && !isConnected) {
      alert('Please wait for connection to backend...')
      return
    }

    if (isListening) {
      setIsListening(false)
      // Stop audio capture by sending message to backend
      if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
        audioSocket.send(JSON.stringify({
          type: 'stop_capture',
          session_id: sessionId,
          timestamp: Date.now()
        }))
      }
    } else {
      // Request audio permission
      const permission = await window.electronAPI?.requestAudioPermission()
      if (permission?.granted) {
        setIsListening(true)
        // Start PyAudio capture by sending message to backend
        if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
          audioSocket.send(JSON.stringify({
            type: 'start_capture',
            session_id: sessionId,
            timestamp: Date.now(),
            audio_config: {
              sample_rate: 16000,
              channels: 1,
              chunk_size: 1024,
              buffer_duration: 1.0
            }
          }))
        }
      } else {
        alert('Microphone permission is required for audio capture')
      }
    }
  }

  const getAgentStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500'
      case 'processing': return 'bg-yellow-500'
      case 'ready': return 'bg-blue-500'
      case 'monitoring': return 'bg-purple-500'
      default: return 'bg-gray-400'
    }
  }

  const getAgentStatusText = (agent: AgentStatus) => {
    if (agent.processing) return 'Processing...'
    return agent.status.charAt(0).toUpperCase() + agent.status.slice(1)
  }

  return (
    <div className={cn("compact-window h-screen overflow-hidden bg-background text-foreground")}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-500/10 to-pink-500/10">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full gradient-primary flex items-center justify-center text-white text-sm font-bold">
            S
          </div>
          <h1 className="font-semibold text-lg">SpeakTogether</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn("w-2 h-2 rounded-full", isConnected ? "bg-green-500" : "bg-red-500")} />
          {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsDarkMode(!isDarkMode)}
          >
            {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
        {/* Main Controls */}
        <Card className="gradient-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Controls</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Caption Toggle */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Live Captions</span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={toggleListening}
                  className={cn(
                    "gap-2 transition-all",
                    isListening ? "gradient-primary text-white" : ""
                  )}
                  variant={isListening ? "default" : "outline"}
                  size="sm"
                >
                  {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                  {isListening ? 'Stop' : 'Start'}
                </Button>
              </div>
            </div>

            {/* Language Selection */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">From</label>
                <Select value={sourceLanguage} onValueChange={setSourceLanguage}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">To</label>
                <Select value={targetLanguage} onValueChange={setTargetLanguage}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.filter(l => l.code !== 'auto').map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* TTS Toggle */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">Text-to-Speech</span>
              <Switch
                checked={isTTSEnabled}
                onCheckedChange={setIsTTSEnabled}
                disabled={true}
              />
            </div>
          </CardContent>
        </Card>

        {/* Live Captions */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Live Captions</CardTitle>
              <Badge variant="secondary" className="text-xs">
                {detectedLanguage}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Original Text */}
            <div className="min-h-[60px] p-3 rounded-md bg-muted/50 text-sm">
              {transcription || (
                <span className="text-muted-foreground italic">
                  {isListening ? "Listening..." : "Start listening to see captions"}
                </span>
              )}
            </div>
            
            {/* Confidence */}
            {transcription && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span>Confidence</span>
                  <span>{confidence.toFixed(0)}%</span>
                </div>
                <Progress value={confidence} className="h-1" />
              </div>
            )}

            <Separator />

            {/* Translation */}
            <div className="min-h-[60px] p-3 rounded-md bg-gradient-to-r from-purple-500/5 to-pink-500/5 text-sm">
              {translation || (
                <span className="text-muted-foreground italic">
                  Translation will appear here
                </span>
              )}
            </div>

            {/* Translation Confidence */}
            {translation && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span>Translation Quality</span>
                  <span>{translationConfidence}%</span>
                </div>
                <Progress value={translationConfidence} className="h-1" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Agent Status - Enhanced visibility */}
        <Card className="border-purple-200 dark:border-purple-800">
          <Accordion type="single" collapsible className="w-full" defaultValue="agents">
            <AccordionItem value="agents" className="border-0">
              <AccordionTrigger className="text-sm font-medium hover:no-underline px-4 py-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-purple-500" />
                  <span className="text-purple-700 dark:text-purple-300">AI Agents</span>
                  {agentData && (
                    <Badge variant="outline" className="ml-2 border-purple-300 text-purple-600">
                      {Object.values(agentData.agents).filter(a => a.processing).length} active
                    </Badge>
                  )}
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-2 px-4 pb-4">
                {agentData ? (
                  Object.entries(agentData.agents).map(([key, agent]) => (
                    <div key={key} className="flex items-center justify-between p-3 rounded-md bg-gradient-to-r from-purple-500/5 to-pink-500/5 border border-purple-200 dark:border-purple-800">
                      <div className="flex items-center gap-2">
                        <div className={cn("w-2 h-2 rounded-full", getAgentStatusColor(agent.status))} />
                        <span className="text-sm font-medium capitalize">
                          {key.replace('_', ' ')}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {getAgentStatusText(agent)}
                      </Badge>
                    </div>
                  ))
                ) : (
                  <div className="p-3 rounded-md bg-muted/30 text-center text-sm text-muted-foreground">
                    No agent data available - start the backend server
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 text-xs mb-4">
          <div className="p-2 rounded-md bg-muted/30">
            <div className="text-muted-foreground">Processing</div>
            <div className="font-medium">{processingTime}</div>
          </div>
          <div className="p-2 rounded-md bg-muted/30">
            <div className="text-muted-foreground">Words</div>
            <div className="font-medium">{wordsProcessed}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Add types for Electron APIs
declare global {
  interface Window {
    electronAPI?: {
      getSessionId: () => Promise<string>
      getBackendUrl: () => Promise<string>
      requestAudioPermission: () => Promise<{ granted: boolean; type: string }>
      openDashboard: () => Promise<void>
      getAppInfo: () => Promise<any>
    }
  }
} 