import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

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
  ChevronDown,
  Monitor,
  MonitorOff
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

// Comprehensive Google Translate supported languages
const languages = [
  { code: 'ab', name: 'Abkhaz' },
  { code: 'ace', name: 'Acehnese' },
  { code: 'ach', name: 'Acholi' },
  { code: 'af', name: 'Afrikaans' },
  { code: 'sq', name: 'Albanian' },
  { code: 'alz', name: 'Alur' },
  { code: 'am', name: 'Amharic' },
  { code: 'ar', name: 'Arabic' },
  { code: 'hy', name: 'Armenian' },
  { code: 'as', name: 'Assamese' },
  { code: 'awa', name: 'Awadhi' },
  { code: 'ay', name: 'Aymara' },
  { code: 'az', name: 'Azerbaijani' },
  { code: 'ban', name: 'Balinese' },
  { code: 'bm', name: 'Bambara' },
  { code: 'ba', name: 'Bashkir' },
  { code: 'eu', name: 'Basque' },
  { code: 'btx', name: 'Batak Karo' },
  { code: 'bts', name: 'Batak Simalungun' },
  { code: 'bbc', name: 'Batak Toba' },
  { code: 'be', name: 'Belarusian' },
  { code: 'bem', name: 'Bemba' },
  { code: 'bn', name: 'Bengali' },
  { code: 'bew', name: 'Betawi' },
  { code: 'bho', name: 'Bhojpuri' },
  { code: 'bik', name: 'Bikol' },
  { code: 'bs', name: 'Bosnian' },
  { code: 'br', name: 'Breton' },
  { code: 'bg', name: 'Bulgarian' },
  { code: 'bua', name: 'Buryat' },
  { code: 'yue', name: 'Cantonese' },
  { code: 'ca', name: 'Catalan' },
  { code: 'ceb', name: 'Cebuano' },
  { code: 'ny', name: 'Chichewa (Nyanja)' },
  { code: 'zh', name: 'Chinese (Simplified)' },
  { code: 'zh-CN', name: 'Chinese (Simplified, China)' },
  { code: 'zh-TW', name: 'Chinese (Traditional)' },
  { code: 'cv', name: 'Chuvash' },
  { code: 'co', name: 'Corsican' },
  { code: 'crh', name: 'Crimean Tatar' },
  { code: 'hr', name: 'Croatian' },
  { code: 'cs', name: 'Czech' },
  { code: 'da', name: 'Danish' },
  { code: 'din', name: 'Dinka' },
  { code: 'dv', name: 'Divehi' },
  { code: 'doi', name: 'Dogri' },
  { code: 'dov', name: 'Dombe' },
  { code: 'nl', name: 'Dutch' },
  { code: 'dz', name: 'Dzongkha' },
  { code: 'en', name: 'English' },
  { code: 'eo', name: 'Esperanto' },
  { code: 'et', name: 'Estonian' },
  { code: 'ee', name: 'Ewe' },
  { code: 'fj', name: 'Fijian' },
  { code: 'fil', name: 'Filipino' },
  { code: 'fi', name: 'Finnish' },
  { code: 'fr', name: 'French' },
  { code: 'fr-CA', name: 'French (Canadian)' },
  { code: 'fy', name: 'Frisian' },
  { code: 'ff', name: 'Fulfulde' },
  { code: 'gaa', name: 'Ga' },
  { code: 'gl', name: 'Galician' },
  { code: 'lg', name: 'Ganda (Luganda)' },
  { code: 'ka', name: 'Georgian' },
  { code: 'de', name: 'German' },
  { code: 'el', name: 'Greek' },
  { code: 'gn', name: 'Guarani' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'ht', name: 'Haitian Creole' },
  { code: 'cnh', name: 'Hakha Chin' },
  { code: 'ha', name: 'Hausa' },
  { code: 'haw', name: 'Hawaiian' },
  { code: 'he', name: 'Hebrew' },
  { code: 'hil', name: 'Hiligaynon' },
  { code: 'hi', name: 'Hindi' },
  { code: 'hmn', name: 'Hmong' },
  { code: 'hu', name: 'Hungarian' },
  { code: 'hrx', name: 'Hunsrik' },
  { code: 'is', name: 'Icelandic' },
  { code: 'ig', name: 'Igbo' },
  { code: 'ilo', name: 'Iloko' },
  { code: 'id', name: 'Indonesian' },
  { code: 'ga', name: 'Irish' },
  { code: 'it', name: 'Italian' },
  { code: 'ja', name: 'Japanese' },
  { code: 'jv', name: 'Javanese' },
  { code: 'kn', name: 'Kannada' },
  { code: 'pam', name: 'Kapampangan' },
  { code: 'kk', name: 'Kazakh' },
  { code: 'km', name: 'Khmer' },
  { code: 'cgg', name: 'Kiga' },
  { code: 'rw', name: 'Kinyarwanda' },
  { code: 'ktu', name: 'Kituba' },
  { code: 'gom', name: 'Konkani' },
  { code: 'ko', name: 'Korean' },
  { code: 'kri', name: 'Krio' },
  { code: 'ku', name: 'Kurdish (Kurmanji)' },
  { code: 'ckb', name: 'Kurdish (Sorani)' },
  { code: 'ky', name: 'Kyrgyz' },
  { code: 'lo', name: 'Lao' },
  { code: 'ltg', name: 'Latgalian' },
  { code: 'la', name: 'Latin' },
  { code: 'lv', name: 'Latvian' },
  { code: 'lij', name: 'Ligurian' },
  { code: 'li', name: 'Limburgan' },
  { code: 'ln', name: 'Lingala' },
  { code: 'lt', name: 'Lithuanian' },
  { code: 'lmo', name: 'Lombard' },
  { code: 'luo', name: 'Luo' },
  { code: 'lb', name: 'Luxembourgish' },
  { code: 'mk', name: 'Macedonian' },
  { code: 'mai', name: 'Maithili' },
  { code: 'mak', name: 'Makassar' },
  { code: 'mg', name: 'Malagasy' },
  { code: 'ms', name: 'Malay' },
  { code: 'ms-Arab', name: 'Malay (Jawi)' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'mt', name: 'Maltese' },
  { code: 'mi', name: 'Maori' },
  { code: 'mr', name: 'Marathi' },
  { code: 'chm', name: 'Meadow Mari' },
  { code: 'mni-Mtei', name: 'Meiteilon (Manipuri)' },
  { code: 'min', name: 'Minang' },
  { code: 'lus', name: 'Mizo' },
  { code: 'mn', name: 'Mongolian' },
  { code: 'my', name: 'Myanmar (Burmese)' },
  { code: 'nr', name: 'Ndebele (South)' },
  { code: 'new', name: 'Nepalbhasa (Newari)' },
  { code: 'ne', name: 'Nepali' },
  { code: 'nso', name: 'Northern Sotho (Sepedi)' },
  { code: 'no', name: 'Norwegian' },
  { code: 'nus', name: 'Nuer' },
  { code: 'oc', name: 'Occitan' },
  { code: 'or', name: 'Odia (Oriya)' },
  { code: 'om', name: 'Oromo' },
  { code: 'pag', name: 'Pangasinan' },
  { code: 'pap', name: 'Papiamento' },
  { code: 'ps', name: 'Pashto' },
  { code: 'fa', name: 'Persian' },
  { code: 'pl', name: 'Polish' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)' },
  { code: 'pt-PT', name: 'Portuguese (Portugal)' },
  { code: 'pa', name: 'Punjabi' },
  { code: 'pa-Arab', name: 'Punjabi (Shahmukhi)' },
  { code: 'qu', name: 'Quechua' },
  { code: 'rom', name: 'Romani' },
  { code: 'ro', name: 'Romanian' },
  { code: 'rn', name: 'Rundi' },
  { code: 'ru', name: 'Russian' },
  { code: 'sm', name: 'Samoan' },
  { code: 'sg', name: 'Sango' },
  { code: 'sa', name: 'Sanskrit' },
  { code: 'gd', name: 'Scots Gaelic' },
  { code: 'sr', name: 'Serbian' },
  { code: 'st', name: 'Sesotho' },
  { code: 'crs', name: 'Seychellois Creole' },
  { code: 'shn', name: 'Shan' },
  { code: 'sn', name: 'Shona' },
  { code: 'scn', name: 'Sicilian' },
  { code: 'szl', name: 'Silesian' },
  { code: 'sd', name: 'Sindhi' },
  { code: 'si', name: 'Sinhala (Sinhalese)' },
  { code: 'sk', name: 'Slovak' },
  { code: 'sl', name: 'Slovenian' },
  { code: 'so', name: 'Somali' },
  { code: 'es', name: 'Spanish' },
  { code: 'su', name: 'Sundanese' },
  { code: 'sw', name: 'Swahili' },
  { code: 'ss', name: 'Swati' },
  { code: 'sv', name: 'Swedish' },
  { code: 'tg', name: 'Tajik' },
  { code: 'ta', name: 'Tamil' },
  { code: 'tt', name: 'Tatar' },
  { code: 'te', name: 'Telugu' },
  { code: 'tet', name: 'Tetum' },
  { code: 'th', name: 'Thai' },
  { code: 'ti', name: 'Tigrinya' },
  { code: 'ts', name: 'Tsonga' },
  { code: 'tn', name: 'Tswana' },
  { code: 'tr', name: 'Turkish' },
  { code: 'tk', name: 'Turkmen' },
  { code: 'ak', name: 'Twi (Akan)' },
  { code: 'uk', name: 'Ukrainian' },
  { code: 'ur', name: 'Urdu' },
  { code: 'ug', name: 'Uyghur' },
  { code: 'uz', name: 'Uzbek' },
  { code: 'vi', name: 'Vietnamese' },
  { code: 'cy', name: 'Welsh' },
  { code: 'xh', name: 'Xhosa' },
  { code: 'yi', name: 'Yiddish' },
  { code: 'yo', name: 'Yoruba' },
  { code: 'yua', name: 'Yucatec Maya' },
  { code: 'zu', name: 'Zulu' }
]

const audioSources = [
  { code: 'microphone', name: 'Microphone' },
  { code: 'system', name: 'System Audio' },
]

// Language Selection Component - Completely isolated from parent state
const IsolatedLanguageSelect = ({ 
  value, 
  onValueChange, 
  placeholder, 
  languages: langList,
  searchPlaceholder = "Search languages...",
  id
}: {
  value: string
  onValueChange: (value: string) => void
  placeholder: string
  languages: Array<{code: string, name: string}>
  searchPlaceholder?: string
  id: string
}) => {
  const [searchValue, setSearchValue] = useState("")
  const [debouncedSearchValue, setDebouncedSearchValue] = useState("")
  const [isOpen, setIsOpen] = useState(false)
  
  // Use a ref to track the previous value
  const prevValue = useRef(value)
  
  // Reset search when value changes from outside
  useEffect(() => {
    if (value !== prevValue.current) {
      setSearchValue("")
      setIsOpen(false)
      prevValue.current = value
    }
  }, [value])
  
  // Debounce the search value to prevent excessive filtering
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchValue(searchValue)
    }, 150)
    return () => clearTimeout(timer)
  }, [searchValue])
  
  const filteredLanguages = useMemo(() => 
    langList.filter(lang => 
      lang.name.toLowerCase().includes(debouncedSearchValue.toLowerCase()) ||
      lang.code.toLowerCase().includes(debouncedSearchValue.toLowerCase())
    ).slice(0, 50) // Limit to 50 results for performance
  , [langList, debouncedSearchValue])

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    setSearchValue(e.target.value)
    if (!isOpen) {
      setIsOpen(true)
    }
  }, [isOpen])

  const handleValueChange = useCallback((newValue: string) => {
    onValueChange(newValue)
    setSearchValue("")
    setIsOpen(false)
  }, [onValueChange])

  const handleInputClick = useCallback(() => {
    setIsOpen(!isOpen)
  }, [isOpen])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
      setSearchValue("")
    }
  }, [])

  const selectedLanguage = useMemo(() => 
    langList.find(lang => lang.code === value)
  , [langList, value])

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest(`#${id}`)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, id])

  return (
    <div className="space-y-1" id={id}>
      <div className="relative">
        <Input
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={handleSearchChange}
          onKeyDown={handleKeyDown}
          onClick={handleInputClick}
          className="h-7 text-xs cursor-pointer"
        />
        {isOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border rounded-md shadow-lg max-h-60 overflow-y-auto">
            {filteredLanguages.map((lang) => (
              <div
                key={lang.code}
                className="px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer flex items-center justify-between"
                onClick={() => handleValueChange(lang.code)}
              >
                <span>{lang.name}</span>
                <span className="text-muted-foreground ml-2">{lang.code}</span>
              </div>
            ))}
            {filteredLanguages.length === 0 && (
              <div className="p-3 text-xs text-muted-foreground text-center">
                No languages found
              </div>
            )}
          </div>
        )}
      </div>
      <div className="text-xs text-muted-foreground">
        Selected: {selectedLanguage?.name || 'None'}
      </div>
    </div>
  )
}

// Simple Language Select with Search - Optimized to prevent re-renders
const SimpleLanguageSelect = React.memo(({ 
  value, 
  onValueChange, 
  placeholder, 
  languages: langList,
  searchPlaceholder = "Search languages..."
}: {
  value: string
  onValueChange: (value: string) => void
  placeholder: string
  languages: Array<{code: string, name: string}>
  searchPlaceholder?: string
}) => {
  const [searchValue, setSearchValue] = useState("")

  const filteredLanguages = useMemo(() => 
    langList.filter(lang => 
      lang.name.toLowerCase().includes(searchValue.toLowerCase()) ||
      lang.code.toLowerCase().includes(searchValue.toLowerCase())
    ).slice(0, 50) // Limit to 50 results for performance
  , [langList, searchValue])

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchValue(e.target.value)
  }, [])

  return (
    <div className="space-y-1">
      <Input
        placeholder={searchPlaceholder}
        value={searchValue}
        onChange={handleSearchChange}
        className="h-7 text-xs"
      />
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="max-h-60">
          {filteredLanguages.map((lang) => (
            <SelectItem key={lang.code} value={lang.code}>
              <div className="flex items-center justify-between w-full">
                <span>{lang.name}</span>
                <span className="text-xs text-muted-foreground ml-2">{lang.code}</span>
              </div>
            </SelectItem>
          ))}
          {filteredLanguages.length === 0 && (
            <div className="p-2 text-xs text-muted-foreground text-center">
              No languages found
            </div>
          )}
        </SelectContent>
      </Select>
    </div>
  )
})

export default function App() {
  // Development mode detection
  const isDev = process.env.NODE_ENV === 'development' || !window.electronAPI

  // State management
  const [isListening, setIsListening] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [transcription, setTranscription] = useState('')
  const [translation, setTranslation] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [translationConfidence, setTranslationConfidence] = useState(0)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [detectedLanguage, setDetectedLanguage] = useState('EN')
  const [sessionId, setSessionId] = useState('')
  const [agentData, setAgentData] = useState<AgentData | null>(null)
  const [audioSource, setAudioSource] = useState('microphone')
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [processingTime, setProcessingTime] = useState('0ms')
  const [wordsProcessed, setWordsProcessed] = useState(0)
  const [isCaptionOverlayEnabled, setIsCaptionOverlayEnabled] = useState(false)

  // WebSocket connections
  const [audioSocket, setAudioSocket] = useState<WebSocket | null>(null)
  const [dashboardSocket, setDashboardSocket] = useState<WebSocket | null>(null)

  // Add throttling references for UI updates
  const lastLanguageUpdate = useRef<number>(0)
  const lastAgentUpdate = useRef<number>(0)
  const lastTranscriptionUpdate = useRef<number>(0)
  const LANGUAGE_UPDATE_THROTTLE = 425 // Reduced by 15%: 500ms → 425ms
  const AGENT_UPDATE_THROTTLE = 85 // Reduced by 15%: 100ms → 85ms  
  const TRANSCRIPTION_UPDATE_THROTTLE = 40 // Reduced by 15%: 50ms → 40ms (ultra fast!)

  // Memoize language change handlers to prevent unnecessary re-renders
  const handleSourceLanguageChange = useCallback((value: string) => {
    setSourceLanguage(value)
    console.log('🔄 Source language changed to:', value)
    
    // Send language update to backend if connected and listening
    if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
      try {
        const message = {
          type: 'update_language_config',
          session_id: sessionId,
          timestamp: Date.now(),
          language_config: {
            source_language: value,
            target_language: targetLanguage
          }
        }
        
        audioSocket.send(JSON.stringify(message))
        console.log('📤 Sent source language update:', {
          source: value,
          target: targetLanguage,
          session_id: sessionId
        })
      } catch (error) {
        console.error('❌ Failed to send source language update:', error)
      }
    } else {
      console.log('⚠️ WebSocket not connected, language update will be sent when capture starts')
    }
  }, [audioSocket, sessionId, targetLanguage])

  const handleTargetLanguageChange = useCallback((value: string) => {
    setTargetLanguage(value)
    console.log('🔄 Target language changed to:', value)
    
    // Send language update to backend if connected and listening
    if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
      try {
        const message = {
          type: 'update_language_config',
          session_id: sessionId,
          timestamp: Date.now(),
          language_config: {
            source_language: sourceLanguage,
            target_language: value
          }
        }
        
        audioSocket.send(JSON.stringify(message))
        console.log('📤 Sent target language update:', {
          source: sourceLanguage,
          target: value,
          session_id: sessionId
        })
      } catch (error) {
        console.error('❌ Failed to send target language update:', error)
      }
    } else {
      console.log('⚠️ WebSocket not connected, language update will be sent when capture starts')
    }
  }, [audioSocket, sessionId, sourceLanguage])

  // Memoize filtered languages to prevent unnecessary re-computation
  const targetLanguages = useMemo(() => 
    languages  // No need to filter anything since auto-detect is removed
  , [])

  // Initialize Electron APIs and WebSocket connections
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Get session ID and backend URL from Electron, with fallbacks for browser mode
        let sessionId = await window.electronAPI?.getSessionId()
        let backendUrl = await window.electronAPI?.getBackendUrl()
        
        // Fallback for browser mode (when Electron APIs aren't available)
        if (!sessionId) {
          sessionId = `browser-session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        }
        
        if (!backendUrl) {
          backendUrl = 'http://localhost:8000'
        }
        
        setSessionId(sessionId)

        // Initialize caption overlay state
        if (window.electronAPI?.isCaptionEnabled) {
          try {
            const captionEnabled = await window.electronAPI.isCaptionEnabled()
            setIsCaptionOverlayEnabled(captionEnabled)
            console.log('Caption overlay state initialized:', captionEnabled)
          } catch (error) {
            console.error('Failed to get caption overlay state:', error)
          }
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
                // Throttle transcription updates to prevent frequent re-renders
                const now = Date.now()
                if (now - lastTranscriptionUpdate.current > TRANSCRIPTION_UPDATE_THROTTLE) {
                                      if (data.transcript && data.transcript.trim()) {
                      setTranscription(data.transcript)
                      setConfidence(data.confidence ? data.confidence * 100 : 0)
                      
                      // Show translation if available
                      if (data.translation && data.translation.text) {
                        setTranslation(data.translation.text)
                        setTranslationConfidence(85) // Default confidence for translation
                        setWordsProcessed(data.transcript.split(' ').length)
                        console.log(`Translation (${data.translation.source_language} → ${data.translation.target_language}):`, data.translation.text)
                        
                        // Update caption overlay
                        updateCaptionOverlay(data.transcript, data.translation.text, data.confidence ? data.confidence * 100 : 0)
                      } else {
                        // Clear translation if not available
                        setTranslation('')
                        setTranslationConfidence(0)
                        setWordsProcessed(data.transcript.split(' ').length)
                        
                        // Update caption overlay with just original text
                        updateCaptionOverlay(data.transcript, '', data.confidence ? data.confidence * 100 : 0)
                      }
                    
                    // Update detected language using selected source language
                    const sourceLang = sourceLanguage.toUpperCase()
                    const confidence = data.confidence ? `${(data.confidence * 100).toFixed(1)}%` : 'N/A'
                    setDetectedLanguage(`${sourceLang} (${confidence})`)
                    
                    // Show service and processing info
                    console.log(`Service: ${data.service_type || 'unknown'} | Processing: ${data.processing_time_ms || 0}ms`)
                  }
                  
                  lastTranscriptionUpdate.current = now
                }
              } else if (data.type === 'audio_chunk') {
                // Handle real audio chunk information
                const audioData = data.audio_data
                const audioMetrics = data.audio_metrics
                
                console.log(`Audio chunk: ${audioData.size_bytes} bytes, Volume: ${audioMetrics.volume_percent.toFixed(1)}%`)
                
                // Throttle detected language updates to prevent frequent re-renders
                const now = Date.now()
                if (audioMetrics.volume_percent > 10 && (now - lastLanguageUpdate.current > LANGUAGE_UPDATE_THROTTLE)) {
                  // Some audio detected - update detected language with volume indicator
                  const lang = sourceLanguage.toUpperCase()
                  setDetectedLanguage(`${lang} (${audioMetrics.volume_percent.toFixed(0)}%)`)
                  lastLanguageUpdate.current = now
                }
              } else if (data.type === 'audio_session_started') {
                console.log('Audio session started:', data.config)
                setIsListening(true)
              } else if (data.type === 'audio_session_ended') {
                console.log('Audio session ended:', data.stats)
                setIsListening(false)
              } else if (data.type === 'transcription_result') {
                // Handle Google Cloud transcription results and AI enhancements
                const result = data.data
                console.log('Transcription Result:', result)
                
                // Check if this is an AI enhancement update
                if (data.is_enhancement && result.translation) {
                  console.log('🤖 Received AI-enhanced translation:', {
                    enhanced: result.translation.text,
                    service: result.translation.service_type,
                    polisher_applied: result.translation.polisher_applied
                  })
                  
                  // Update only the translation with the enhanced version
                  setTranslation(result.translation.text)
                  setTranslationConfidence(90) // Higher confidence for AI-enhanced
                  
                  // Update caption overlay with enhanced translation
                  updateCaptionOverlay(result.transcript, result.translation.text, result.confidence ? result.confidence * 100 : 0)
                  
                  console.log(`🚀 Enhanced Translation: ${result.translation.text}`)
                  return // Don't process as regular transcription result
                }
                
                // Handle regular transcription results (instant polished)
                const now = Date.now()
                if (now - lastTranscriptionUpdate.current > TRANSCRIPTION_UPDATE_THROTTLE) {
                  if (result.transcript && result.transcript.trim()) {
                    setTranscription(result.transcript)
                    setConfidence(result.confidence ? result.confidence * 100 : 0)
                    
                    // Show translation if available (instant polished version)
                    if (result.translation && result.translation.text) {
                      setTranslation(result.translation.text)
                      
                      // Set confidence based on polisher status
                      const polisherApplied = result.translation.polisher_applied
                      setTranslationConfidence(polisherApplied ? 85 : 75)
                      setWordsProcessed(result.transcript.split(' ').length)
                      
                      console.log(`🔧 ${polisherApplied ? 'Polished' : 'Raw'} Translation (${result.translation.source_language} → ${result.translation.target_language}):`, result.translation.text)
                      
                      // Update caption overlay for direct transcription results
                      updateCaptionOverlay(result.transcript, result.translation.text, result.confidence ? result.confidence * 100 : 0)
                    } else {
                      // Clear translation if not available
                      setTranslation('')
                      setTranslationConfidence(0)
                      setWordsProcessed(result.transcript.split(' ').length)
                      
                      // Update caption overlay with just original text
                      updateCaptionOverlay(result.transcript, '', result.confidence ? result.confidence * 100 : 0)
                    }
                    
                    // Update detected language
                    const lang = result.language_detected || sourceLanguage
                    const confidence = result.confidence ? `${(result.confidence * 100).toFixed(1)}%` : 'N/A'
                    setDetectedLanguage(`${lang.toUpperCase()} (${confidence})`)
                    
                    // Show service and processing info with polisher status
                    const serviceInfo = result.translation?.polisher_applied 
                      ? `${result.service_type || 'unknown'} + Polisher` 
                      : result.service_type || 'unknown'
                    console.log(`Service: ${serviceInfo} | Processing: ${result.processing_time_ms || 0}ms`)
                  }
                  
                  lastTranscriptionUpdate.current = now
                }
                
                setIsTranscribing(false)
              } else if (data.type === 'error') {
                console.error('Backend error:', data.message)
                setIsListening(false)
                alert(`Audio error: ${data.message}`)
              } else if (data.type === 'language_config_updated') {
                // Handle language configuration update confirmation
                console.log('✅ Language configuration updated successfully:', data.config)
                
                // Update detected language display to show new configuration
                const sourceLabel = languages.find(lang => lang.code === data.config.source_language)?.name || data.config.source_language
                const targetLabel = languages.find(lang => lang.code === data.config.target_language)?.name || data.config.target_language
                
                console.log(`🌐 Language configuration: ${sourceLabel} → ${targetLabel}`)
              } else if (data.type === 'audio_source_status') {
                // Handle audio source status updates
                console.log('🔊 Audio source status:', data)
                
                if (data.status === 'fallback' && data.requested_source === 'system' && data.actual_source === 'microphone') {
                  // System audio was requested but fell back to microphone
                  console.warn('⚠️ System audio fallback:', data.message)
                  
                  // Show user-friendly notification
                  const platform = navigator.platform.toLowerCase()
                  let setupInstructions = ''
                  
                  if (platform.includes('mac')) {
                    setupInstructions = 'Install BlackHole from https://github.com/ExistentialAudio/BlackHole to enable system audio capture.'
                  } else if (platform.includes('win')) {
                    setupInstructions = 'Enable "Stereo Mix" in Windows sound settings or install VB-Cable to enable system audio capture.'
                  } else {
                    setupInstructions = 'Configure PulseAudio monitor or ALSA loopback to enable system audio capture.'
                  }
                  
                  alert(`System Audio Not Available\n\nSpeakTogether is using your microphone instead of system audio.\n\n${setupInstructions}`)
                  
                  // Update detected language to show the actual source
                  setDetectedLanguage(`MICROPHONE (fallback from system audio)`)
                } else if (data.status === 'success' && data.actual_source === 'system') {
                  // System audio is working correctly
                  console.log('✅ System audio active:', data.device_name)
                  setDetectedLanguage(`SYSTEM AUDIO (${data.device_name})`)
                }
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
            // Throttle agent data updates to prevent frequent re-renders
            const now = Date.now()
            if (now - lastAgentUpdate.current > AGENT_UPDATE_THROTTLE) {
              setAgentData(data)
              lastAgentUpdate.current = now
            }
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
      setIsTranscribing(false)
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
        setIsTranscribing(true)
        // Start PyAudio capture by sending message to backend
        if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
          audioSocket.send(JSON.stringify({
            type: 'start_capture',
            session_id: sessionId,
            timestamp: Date.now(),
            audio_config: {
              sample_rate: 16000,
              channels: audioSource === 'system' ? 2 : 1,  // Stereo for system audio
              chunk_size: 1024,
              buffer_duration: 1.0,
              audio_source: audioSource,
              source_language: sourceLanguage,  // Use current state
              target_language: targetLanguage   // Use current state
            }
          }))
          
          console.log('📤 Sent start_capture with language config:', {
            source_language: sourceLanguage,
            target_language: targetLanguage,
            audio_source: audioSource,
            session_id: sessionId
          })
        }
      } else {
        alert(`${audioSource === 'system' ? 'System audio' : 'Microphone'} permission is required for audio capture`)
      }
    }
  }

  // Handle caption overlay toggle
  const toggleCaptionOverlay = async () => {
    console.log('🎮 toggleCaptionOverlay button clicked')
    console.log('🎮 Current state:', isCaptionOverlayEnabled)
    console.log('🎮 electronAPI available:', !!window.electronAPI)
    
    // First get debug state to understand current situation
    if (window.electronAPI?.debugCaptionState) {
      try {
        const debugState = await window.electronAPI.debugCaptionState()
        console.log('🔍 Current debug state:', debugState)
      } catch (debugError) {
        console.error('🔍 Failed to get debug state:', debugError)
      }
    }
    
    try {
      const newState = !isCaptionOverlayEnabled
      console.log('🎮 Attempting to set new state:', newState)
      
      if (!window.electronAPI?.toggleCaptionOverlay) {
        console.error('🎮 toggleCaptionOverlay API not available')
        alert('Caption overlay API not available. Please ensure you\'re running in Electron.')
        return
      }
      
      console.log('🎮 Calling electronAPI.toggleCaptionOverlay...')
      const result = await window.electronAPI.toggleCaptionOverlay(newState)
      console.log('🎮 Got result from main process:', result)
      
      if (result?.success) {
        setIsCaptionOverlayEnabled(newState)
        console.log('✅ Caption overlay toggled successfully:', newState)
        
        // Log final state for debugging
        if (result.state) {
          console.log('📊 Final window state:', result.state)
          
          // Show success message with details
          if (newState && result.state.windowVisible) {
            console.log('🎉 Caption window should now be visible on screen!')
          } else if (newState && !result.state.windowVisible) {
            console.warn('⚠️ Caption window created but not visible - check always-on-top settings')
          }
        }
        
      } else {
        console.error('❌ Failed to toggle caption overlay:', result?.error)
        console.error('❌ Error stack:', result?.stack)
        
        // Enhanced error reporting
        let errorMessage = `Failed to toggle caption overlay: ${result?.error || 'Unknown error'}`
        if (result?.stack) {
          errorMessage += '\n\nTechnical details logged to console.'
        }
        alert(errorMessage)
      }
    } catch (error) {
      console.error('❌ Critical error toggling caption overlay:', error)
      alert('Failed to toggle caption overlay. This feature requires Electron.')
    }
  }

  // Debug function to force show window (for testing)
  const debugForceShowWindow = async () => {
    if (!window.electronAPI?.forceShowCaptionWindow) {
      alert('Debug API not available')
      return
    }
    
    try {
      console.log('🧪 Forcing caption window to show...')
      const result = await window.electronAPI.forceShowCaptionWindow()
      console.log('🧪 Force show result:', result)
      
      if (result) {
        alert('Caption window forced to show. Check if it\'s visible on screen.')
      } else {
        alert('Failed to force show caption window. Check console for details.')
      }
    } catch (error) {
      console.error('🧪 Error forcing show:', error)
      alert('Error forcing caption window to show.')
    }
  }

  // Send caption data to overlay window
  const updateCaptionOverlay = useCallback((original: string, translated: string, confidence: number) => {
    console.log('📤 updateCaptionOverlay called:', { 
      original, 
      translated, 
      confidence, 
      isCaptionOverlayEnabled,
      hasElectronAPI: !!window.electronAPI?.updateCaptionText
    });
    
    // ENHANCED DEBUGGING: Log detailed translation info
    console.log('🔍 TRANSLATION DEBUG:', {
      'translated_param': translated,
      'translated_length': translated?.length || 0,
      'translated_type': typeof translated,
      'translated_truthy': !!translated,
      'original_vs_translated': original === translated ? 'SAME' : 'DIFFERENT'
    });
    
    if (window.electronAPI?.updateCaptionText) {
      console.log('📤 Sending real transcription to caption overlay:', { original, translated, confidence });
      
      // Always send real transcription data to caption window (even if overlay appears disabled)
      // The caption window itself will handle whether to display it
      window.electronAPI.updateCaptionText({
        original,
        translation: translated || '',  // Fixed: use 'translation' property name and remove restrictive condition
        confidence,
        fromTranscription: true, // Mark as real transcription data
        timestamp: Date.now(),
        language: sourceLanguage || 'en', // Include language for font selection
        isRealTime: true // Flag to force override test mode
      }).then(result => {
        console.log('✅ Caption update result:', result);
      }).catch(error => {
        console.error('❌ Caption update failed:', error);
      });
    } else {
      console.warn('⚠️ electronAPI.updateCaptionText not available');
    }
  }, [isCaptionOverlayEnabled, sourceLanguage])

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

            {/* Audio Source Selection */}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Audio Source</label>
              <Select value={audioSource} onValueChange={setAudioSource}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {audioSources.map((source) => (
                    <SelectItem key={source.code} value={source.code}>
                      {source.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Language Selection */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">From</label>
                <IsolatedLanguageSelect
                  value={sourceLanguage}
                  onValueChange={handleSourceLanguageChange}
                  placeholder="Select source language"
                  languages={languages}
                  searchPlaceholder="Search source languages..."
                  id="source-language-select"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">To</label>
                <IsolatedLanguageSelect
                  value={targetLanguage}
                  onValueChange={handleTargetLanguageChange}
                  placeholder="Select target language"
                  languages={targetLanguages}
                  searchPlaceholder="Search target languages..."
                  id="target-language-select"
                />
              </div>
            </div>

            {/* Floating Caption Overlay */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Floating Overlay</span>
              <Button
                onClick={toggleCaptionOverlay}
                className={cn(
                  "gap-2 transition-all",
                  isCaptionOverlayEnabled ? "gradient-primary text-white" : ""
                )}
                variant={isCaptionOverlayEnabled ? "default" : "outline"}
                size="sm"
              >
                {isCaptionOverlayEnabled ? <Monitor className="w-4 h-4" /> : <MonitorOff className="w-4 h-4" />}
                {isCaptionOverlayEnabled ? 'On' : 'Off'}
              </Button>
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
      
      // Caption overlay controls
      toggleCaptionOverlay: (enabled: boolean) => Promise<{ success: boolean; enabled?: boolean; error?: string; state?: any }>
      updateCaptionText: (data: { 
        original: string; 
        translation: string; // Fixed: changed from 'translated' to 'translation'
        confidence: number;
        fromTranscription?: boolean;
        timestamp?: number;
        language?: string; // Added for font selection
        isRealTime?: boolean; // Added for force override
      }) => Promise<{ success: boolean; error?: string }>
      isCaptionEnabled: () => Promise<boolean>
      
      // Debugging and testing
      debugCaptionState: () => Promise<any>
      forceShowCaptionWindow: () => Promise<boolean>
    }
  }
} 