package com.example.ws_ms_detectionAnomalie.services;



import com.example.ws_ms_detectionAnomalie.repositories.V_HotelReservation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Service
public class V_HotelReservationService {

    @Autowired
    private V_HotelReservation reservationRepository;

    public List<Map<String, Object>> getAllReservations(BigDecimal idEntite) {
        return reservationRepository.findListReservationsByIdEntite(idEntite);
    }
}