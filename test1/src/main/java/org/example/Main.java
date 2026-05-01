package org.example;

import java.util.Scanner;

public class Main {
    public static void main(String[] args) {

        for (int day = 1; day <= 5; day++) {

            System.out.println("Day" + day);

            for (int hour = 9; hour < 18; hour++) {
                System.out.println(hour + " -> " + (hour + 1));
            }

            System.out.println();
        }
    }
}
