package com.gaia.game.room.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "rooms")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Room {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;

    private int maxPlayers;

    @Enumerated(EnumType.STRING)
    private RoomStatus status;

    public Room(String title, int maxPlayers) {
        this.title = title;
        this.maxPlayers = maxPlayers;
        this.status = RoomStatus.WAITING;
    }

    public void start() {
        this.status = RoomStatus.PLAYING;
    }
}
