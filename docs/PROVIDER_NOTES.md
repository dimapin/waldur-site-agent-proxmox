<!-- Vendored from waldur-multicloud tag contract-v1, path docs/providers/proxmox.md. -->

# Proxmox VE (`proxmoxer`)
- Operationen liefern Task-UPID; Status aktiv pollen (Timeout +
  Obergrenze). Erfolg == Task OK.
- Keine Flavors/Images im Cloud-Sinn: Mapping Node + Template + VMID
  ist Plugin-Config, keine Code-Konstante.
- VMID: immer per API (nextid) beziehen, Konfliktantworten behandeln —
  klassische Kollisionsquelle bei parallelen Orders.
- Nutzer-/Berechtigungsmodell vorhanden → membership_sync-Kandidat,
  Umfang vor Implementierung klaeren.
