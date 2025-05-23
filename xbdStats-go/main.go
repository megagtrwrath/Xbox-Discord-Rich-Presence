package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
	"github.com/hugolgst/rich-go/client"
)

const (
	clientID = "1304454011503513600"
	APIURL   = "https://mobcat.zip/XboxIDs"
	CDNURL   = "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon"
)

type TitleLookup struct {
	XMID     string `json:"XMID"`
	FullName string `json:"Full_Name"`
}

type GameMessage struct {
	ID    string `json:"id"`
	Name  string `json:"name,omitempty"`
	Xenon bool   `json:"xbox360,omitempty"` // xbox360 override, system still defaults to Xbox.
}

var xbox360Titles = map[string]string{}

func loadXbox360Titles(path string) {
	file, err := os.Open(path)
	if err != nil {
		log.Printf("Could not open xbox360.json: %v", err)
		return
	}
	defer file.Close()

	var entries []struct {
		TitleID string `json:"TitleID"`
		Title   string `json:"Title"`
	}
	if err := json.NewDecoder(file).Decode(&entries); err != nil {
		log.Printf("Invalid JSON in xbox360.json: %v", err)
		return
	}

	for _, e := range entries {
		tid := strings.ToUpper(e.TitleID)
		xbox360Titles[tid] = e.Title
	}
	log.Printf("Loaded %d Xbox 360 titles", len(xbox360Titles))
}

func connectRPC() error {
	return client.Login(clientID)
}

func setPresence(titleID, titleName, xmid string) error {
	start := time.Now()

	var largeImage string
	var largeText string
	var smallImage string

	// default to mobcats api/icon sets.
	switch xmid {
	case "00000000":
		largeImage = "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0FFE/0FFEEFF0.png"
		largeText = titleName
		smallImage = "https://cdn.discordapp.com/avatars/1304454011503513600/6be191f921ebffb2f9a52c1b6fc26dfa"
	case "XBOX360":
		largeImage = "https://raw.githubusercontent.com/MrMilenko/testgit/main/xbox360.png"
		largeImage = fmt.Sprintf("http://xboxunity.net/Resources/Lib/Icon.php?tid=%s", titleID)
		largeText = fmt.Sprintf("%s (Xbox 360)", titleName)
		smallImage = "https://raw.githubusercontent.com/MrMilenko/testgit/main/xbox360.png"
	default:
		largeImage = fmt.Sprintf("%s/%s/%s.png", CDNURL, titleID[:4], titleID)
		largeText = fmt.Sprintf("TitleID: %s", titleID)
		smallImage = "https://cdn.discordapp.com/avatars/1304454011503513600/6be191f921ebffb2f9a52c1b6fc26dfa"
	}

	// Only include button if API gave a valid XMID
	var buttons []*client.Button
	if xmid != "00000000" {
		buttons = []*client.Button{
			{
				Label: "Title Info",
				Url:   fmt.Sprintf("%s/title.php?%s", APIURL, xmid),
			},
		}
	}

	return client.SetActivity(client.Activity{
		Details: titleName,
		Timestamps: &client.Timestamps{
			Start: &start,
		},
		LargeImage: largeImage,
		LargeText:  largeText,
		SmallImage: smallImage,
		Buttons:    buttons,
	})
}

func clearPresence() {
	// fake-clear by overwriting with a blank activity (literally no idea if this works)
	_ = client.SetActivity(client.Activity{})
}

func lookupID(titleID string) (string, string) {
	url := fmt.Sprintf("%s/api.php?id=%s", APIURL, titleID)
	resp, err := http.Get(url)
	if err != nil {
		log.Printf("Lookup error: %v", err)
		return "00000000", "Unknown Title"
	}
	defer resp.Body.Close()

	var result []TitleLookup
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil || len(result) == 0 {
		log.Printf("Invalid JSON or empty result for titleID %s", titleID)
		return "00000000", "Unknown Title"
	}
	return result[0].XMID, result[0].FullName
}

// Added TCP because macOS told me to fuck off when I tried to use UDP
func handleTCP() {
	addr := "0.0.0.0:1103"
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("[TCP] Bind failed: %v", err)
	}
	defer listener.Close()
	log.Println("[TCP] Listening on port 1103")

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("[TCP] Accept error: %v", err)
			continue
		}

		go func(c net.Conn) {
			defer c.Close()

			buf := make([]byte, 1024)
			n, err := c.Read(buf)
			if err != nil {
				log.Printf("[TCP] Read error: %v", err)
				return
			}

			var msg GameMessage
			if err := json.Unmarshal(buf[:n], &msg); err != nil {
				log.Printf("[TCP] Bad JSON from %v: %v", c.RemoteAddr(), err)
				return
			}

			var title, xmid string
			if msg.Xenon {
				xmid = "XBOX360"
				id := strings.ToUpper(msg.ID)
				if t, ok := xbox360Titles[id]; ok {
					title = t
				} else {
					log.Printf("Xbox 360 fallback missing titleID %s", id)
					title = msg.Name
				}

			} else {
				xmid, title = lookupID(msg.ID)
				if title == "Unknown Title" && msg.Name != "" {
					title = msg.Name
				}
			}

			setPresence(msg.ID, title, xmid)
			log.Printf("[TCP] From %s: %s", c.RemoteAddr().String(), string(buf[:n]))
			log.Printf("[TCP] Now Playing %s (%s) - %s [Xenon: %v]", msg.ID, xmid, title, msg.Xenon)
		}(conn)
	}
}

func handleUDP() {
	addr := net.UDPAddr{Port: 1102, IP: net.ParseIP("0.0.0.0")}
	sock, err := net.ListenUDP("udp", &addr)
	if err != nil {
		log.Fatalf("UDP bind failed: %v", err)
	}
	defer sock.Close()
	log.Println("[UDP] Listening on port 1102")

	buf := make([]byte, 1024)
	for {
		n, remote, err := sock.ReadFromUDP(buf)
		if err != nil {
			log.Printf("[UDP] Read error: %v", err)
			continue
		}

		var msg GameMessage
		if err := json.Unmarshal(buf[:n], &msg); err != nil {
			log.Printf("[UDP] Bad JSON from %v: %v", remote, err)
			continue
		}

		var title, xmid string
		if msg.Xenon {
			xmid = "XBOX360"
			id := strings.ToUpper(msg.ID)
			if t, ok := xbox360Titles[id]; ok {
				title = t
			} else {
				log.Printf("Xbox 360 fallback missing titleID %s", id)
				title = msg.Name
			}

		} else {
			xmid, title = lookupID(msg.ID)
			if title == "Unknown Title" && msg.Name != "" {
				title = msg.Name
			}
		}

		setPresence(msg.ID, title, xmid)
		log.Printf("[UDP] From %s: %s", remote, string(buf[:n]))
		log.Printf("[UDP] Now Playing %s (%s) - %s [Xenon: %v]", msg.ID, xmid, title, msg.Xenon)
	}
}
func handleWebsocket() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		conn, err := websocket.Upgrade(w, r, nil, 1024, 1024)
		if err != nil {
			log.Println("WebSocket error:", err)
			return
		}
		defer conn.Close()
		log.Printf("[WebSocket] Client connected: %s", r.RemoteAddr)

		for {
			_, msg, err := conn.ReadMessage()
			if err != nil {
				log.Printf("[WebSocket] Read error: %v", err)
				break
			}

			var gm GameMessage
			if err := json.Unmarshal(msg, &gm); err != nil {
				log.Printf("[WebSocket] Bad JSON: %v", err)
				continue
			}

			var title, xmid string
			if gm.Xenon {
				xmid = "XBOX360"
				id := strings.ToUpper(gm.ID)
				if t, ok := xbox360Titles[id]; ok {
					title = t
				} else {
					log.Printf("Xbox 360 fallback missing titleID %s", id)
					title = gm.Name
				}

			} else {
				xmid, title = lookupID(gm.ID)
				if title == "Unknown Title" && gm.Name != "" {
					title = gm.Name
				}
			}

			setPresence(gm.ID, title, xmid)
			log.Printf("[WebSocket] From %s: %s", conn.RemoteAddr().String(), string(msg))
			log.Printf("[WebSocket] Now Playing %s (%s) - %s [xenon: %v]", gm.ID, xmid, title, gm.Xenon)
		}
	})

	log.Println("[WebSocket] Listening on 1101")
	log.Fatal(http.ListenAndServe(":1101", nil))
}

func main() {
	fmt.Println(`
      _         _ __ _         _       
__  _| |__   __| / _\ |_  __ _| |_ ___ 
\ \/ / '_ \ / _` + "`" + ` \ \| __|/ _` + "`" + ` | __/ __|
 >  <| |_) | (_| |\ \ |_  (_| | |_\__ \\
/_/\_\_.__/ \__,_\__/\__|\__,_|\__|___/
xbdStats-go Server 20250521
`)
	log.Println("Loading Xbox 360 titles from xbox360.json")
	loadXbox360Titles("xbox360.json")
	if err := connectRPC(); err != nil {
		log.Fatalf("Could not connect to Discord: %v", err)
	}
	defer func() {
		clearPresence()
		client.Logout() // note: doesn't return anything lol
	}()

	go handleTCP()
	go handleUDP()
	go handleWebsocket()

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	<-sigs
	log.Println("Shutdown received. Cleaning up...")
	log.Println("Clean shutdown.")
}
