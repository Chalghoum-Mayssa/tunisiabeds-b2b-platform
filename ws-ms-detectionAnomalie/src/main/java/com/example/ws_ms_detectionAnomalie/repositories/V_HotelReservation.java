package com.example.ws_ms_detectionAnomalie.repositories;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Repository
public class V_HotelReservation {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    public List<Map<String, Object>> findListReservationsByIdEntite(BigDecimal idEntite) {
        String sql = "SELECT * FROM V_HOTEL_RESERVATION WHERE ID_ENTITE = ?";
        return jdbcTemplate.queryForList(sql, idEntite);
    }
}