set -eux

USERNAME=$1
IDX=$(( 10 + $(wc -l /etc/wireguard/wg0.conf | awk '{print $1}') / 6 ))
PRIVATEKEY=$(wg genkey)

cat > ${USERNAME}.wg << EOF
[Interface]
Address = 10.0.0.${IDX}/24
Address = fc00::${IDX}/7
PrivateKey = ${PRIVATEKEY}

[Peer]
Endpoint = eastpaloalto.jaminais.fr:51
PublicKey = INeCR3uB2Z+0v68pntWDV+awELG1GOKsLJ9xzvkv01Q=
AllowedIPs = 0.0.0.0/0, ::/0
EOF

cat >> /etc/wireguard/wg0.conf << EOF

[Peer]
# ${USERNAME}
PublicKey = $(echo ${PRIVATEKEY} | wg pubkey)
AllowedIPs = 10.0.0.${IDX}/32
AllowedIPs = fc00::${IDX}/128
EOF

wg-quick down wg0
wg-quick up wg0

qrencode -t ansiutf8 < ${USERNAME}.wg
