package com.example.ws_ms_detectionAnomalie.controllers;

import com.example.ws_ms_detectionAnomalie.services.*;
import com.example.ws_ms_detectionAnomalie.services.V_HotelReservationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@CrossOrigin(origins = "http://localhost:4200")
@RestController
@RequestMapping("/ReservationView")
public class ViewController {

    @Autowired
    private V_HotelReservationService reservationService;

    @GetMapping("/reservations/{idEntite}")
    public List<Map<String, Object>> getReservationsByEntite(@PathVariable BigDecimal idEntite) {
        return reservationService.getAllReservations(idEntite);
    }

}