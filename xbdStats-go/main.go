package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
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
	ID       string `json:"id"`
	Name     string `json:"name,omitempty"`
	Override bool   `json:"override,omitempty"`
}

func connectRPC() error {
	return client.Login(clientID)
}

func setPresence(titleID, titleName, xmid string) error {
	start := time.Now()

	var largeImage string
	var largeText string

	// If the TitleID is clearly invalid (homebrew IDs or forced override), use fallback logo
	if titleID == "00000000" || titleName == "Unknown Title" {
		largeImage = "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0FFE/0FFEEFF0.png"
		largeText = titleName
	} else {
		// Even if API fails, try the CDN icon path anyway
		largeImage = fmt.Sprintf("%s/%s/%s.png", CDNURL, titleID[:4], titleID)
		largeText = fmt.Sprintf("TitleID: %s", titleID)
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
		SmallImage: "https://cdn.discordapp.com/avatars/1304454011503513600/6be191f921ebffb2f9a52c1b6fc26dfa",
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
			if msg.Override {
				title = msg.Name
				xmid = "00000000"
			} else {
				xmid, title = lookupID(msg.ID)
				if title == "Unknown Title" && msg.Name != "" {
					title = msg.Name
				}
			}

			setPresence(msg.ID, title, xmid)
			log.Printf("[TCP] From %s: %s", c.RemoteAddr().String(), string(buf[:n]))
			log.Printf("[TCP] Now Playing %s (%s) - %s [override: %v]", msg.ID, xmid, title, msg.Override)
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
		if msg.Override {
			title = msg.Name
			xmid = "00000000"
		} else {
			xmid, title = lookupID(msg.ID)
			if title == "Unknown Title" && msg.Name != "" {
				title = msg.Name
			}
		}

		setPresence(msg.ID, title, xmid)
		log.Printf("[UDP] From %s: %s", remote, string(buf[:n]))
		log.Printf("[UDP] Now Playing %s (%s) - %s [override: %v]", msg.ID, xmid, title, msg.Override)
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
			if gm.Override {
				title = gm.Name
				xmid = "00000000"
			} else {
				xmid, title = lookupID(gm.ID)
				if title == "Unknown Title" && gm.Name != "" {
					title = gm.Name
				}
			}

			setPresence(gm.ID, title, xmid)
			log.Printf("[WebSocket] From %s: %s", conn.RemoteAddr().String(), string(msg))
			log.Printf("[WebSocket] Now Playing %s (%s) - %s [override: %v]", gm.ID, xmid, title, gm.Override)
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
