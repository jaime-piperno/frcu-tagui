const users = [
  { name: 'standard_user', shouldPass: true },
  { name: 'locked_out_user', shouldPass: false },
  { name: 'problem_user', shouldPass: false },
  { name: 'performance_glitch_user', shouldPass: false },
  { name: 'error_user', shouldPass: false },
  { name: 'visual_user', shouldPass: false }
]

describe('Flujo de compra en SauceDemo con distintos usuarios', () => {

  users.forEach(user => {
    it(`Compra con ${user.name}`, () => {
      cy.visit('https://www.saucedemo.com/')
      cy.get('#user-name').type(user.name)
      cy.get('#password').type('secret_sauce')
      cy.get('#login-button').click()
      cy.get('#add-to-cart-sauce-labs-backpack').click()
      cy.get('.shopping_cart_link').click()
      cy.get('#checkout').click()
      cy.get('#first-name').type('Manu')
      cy.get('#last-name').type('Riedel')
      cy.get('#postal-code').type('3260')
      cy.get('#continue').click()
      cy.get('#finish').click()

      cy.contains('h2', 'Thank you for your order!').should(
        user.shouldPass ? 'be.visible' : 'not.exist'
      )
    })
  })

})
